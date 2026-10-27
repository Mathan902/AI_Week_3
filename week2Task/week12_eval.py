"""Week 12: the eval suite, run against the INTEGRATED engine (week12_engine.Engine), not against its parts.

    .venv/bin/python week12_eval.py run --release r2 --label r2_a        # 32 cases: answers -> assertions -> trajectory
    .venv/bin/python week12_eval.py sheet --run r2_a                     # blind labelling sheet for that run
    .venv/bin/python week12_eval.py lock-labels --run r2_a               # freeze the hand labels BEFORE any judge run
    .venv/bin/python week12_eval.py judge --run r2_a                     # Week 6 judge_v2 on these outputs + agreement
    .venv/bin/python week12_eval.py report --runs r0_a r1_a r2_a         # every table -> week12/eval_report_tables.md
    .venv/bin/python week12_eval.py case C01 --release r2                # one case, RED/GREEN (the failure -> test loop)

Assertions before judges: every criterion a parser, a symbol table or a regex can check is an assertion. The judge
keeps the one binary criterion Week 6 validated ("directly answers"), and it is re-checked on THESE outputs.
The trajectory eval (Week 8 method) scores the tool calls in the same traces, so it costs nothing extra.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import week12_guards as g
from week12_engine import LOG_DIR, RELEASES, Engine

ROOT = Path(__file__).parent
W12 = ROOT / "week12"
CASES_FILE = W12 / "eval_cases.jsonl"
RUNS = W12 / "runs"
LABELS = W12 / "labels"
CONCURRENCY = 4
MODES = {  # what each case guards; the re-scored taxonomy (week12/taxonomy.md) is built from the traces
    "W1": "Code for the wrong SDK version (a v2 caller gets v3 code, or v3 gets v2)",
    "W2": "Removed/renamed API not called out plainly for a v3 caller",
    "W3": "Changed default answered without the version difference",
    "W4": "Invented method or signature for something that does not exist",
    "W5": "Coverage: answers from the other version's docs, or refuses what the docs answer",
    "W7": "Pasted secret reaches the model, the MCP server or a log line",
    "W8": "Integration: redaction-on-write corrupts an emitted code sample (regression, C18 tr-5871db30a290)",
}
REFUSAL = re.compile(r"I don't know|don't cover|do not cover|doesn't cover|not covered|no (published )?docs|"
                     r"is(?:n't| not) (?:a )?documented|not documented|(?:is(?:n't| not)|not) published|not in the (docs|documentation)|"
                     r"no documentation|does not (exist|support)|doesn't (exist|support)|not (available|supported)|"
                     r"there (is|are) no\b", re.I)
PLAIN = re.compile(r"no longer exists|(was |is |been |were )?removed in (SDK )?(v?3|3\.0)|does not exist in|"
                   r"doesn't exist in|renamed (in|to)|was renamed|no longer (available|supported|part)", re.I)
NOTE_WORDS = re.compile(r"removed|renamed|no longer|replaced|changed|upgrade|deprecat", re.I)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(b: bytes | str) -> str:
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def load_cases(ids: list[str] | None = None) -> list[dict]:
    cases = [json.loads(l) for l in CASES_FILE.read_text().splitlines() if l.strip()]
    return [c for c in cases if not ids or c["id"] in ids]


# ---------------------------------------------------------------- assertions (deterministic)

def _code(trace: dict) -> str:
    return (trace.get("output") or {}).get("code", "") or ""


def a_version_resolved(c, t):
    v = t["version"]
    ok = v["major"] == c["version_major"] and v["code_target"] == c["code_target"]
    return ("pass" if ok else "fail", f"{v['minor']}->{v['major']}/code {v['code_target']} via {v['source']}")


def a_code_presence(c, t):
    code = _code(t)
    if c["code"] == "required":
        return ("pass", "code present") if code else ("fail", "no code sample")
    if c["code"] == "forbidden":
        return ("pass", "no code") if not code else ("fail", "code given where the docs have none for this version")
    return "n/a", "either"


def a_code_parses(c, t):  # the Week 6 bar: "looks like code"
    code = _code(t)
    if not code:
        return "n/a", "no code"
    try:
        ast.parse(code)
        return "pass", "parses"
    except SyntaxError as exc:
        return "fail", f"SyntaxError: {exc.msg}"


def a_code_runs_on_version(c, t):  # the Week 12 bar: parses AND every import / method / parameter exists THERE
    code = _code(t)
    if not code:
        return "n/a", "no code"
    r = g.check_code(code, c["code_target"])
    return r["status"], "; ".join(r["violations"]) or f"{r['checked']} symbols exist in {c['code_target']}"


def a_code_must_not(c, t):
    code = _code(t)
    if not c["code_must_not"] or not code:
        return "n/a", "nothing banned" if not c["code_must_not"] else "no code"
    hit = [p for p in c["code_must_not"] if re.search(p, code)]
    return ("fail", f"code matches /{hit[0]}/") if hit else ("pass", "clear")


def a_cites_version(c, t):
    if c["expect"] != "answer" or not c["cite_version"]:
        return "n/a", "no citation target"
    cites = t.get("citations") or []
    if not cites:
        return "fail", "no citation"
    if any(not x.get("sdk_version") for x in cites):
        return "fail", "a citation names no SDK version"
    first = cites[0]["sdk_version"]
    return ("pass", f"first cites {first}") if first == c["cite_version"] else \
        ("fail", f"first citation is {first} ({cites[0]['id']}), caller needs {c['cite_version']}")


def a_citations_grounded(c, t):
    cites = t.get("citations") or []
    if not cites:
        return "n/a", "no citations"
    bad = [x["id"] for x in cites if not x.get("grounded")]
    return ("fail", f"not returned by any tool: {bad[0]}") if bad else ("pass", f"{len(cites)} grounded")


def a_deprecation_surfaced(c, t):
    if not c["must_notice"]:
        return "n/a", "nothing to surface"
    text = t["answer_text"]
    missing = []
    for sym in c["must_notice"]:
        pat = r"(?:[Cc]lient\.|\.)request\b" if sym == "request" else rf"\b{re.escape(sym)}\b"
        windows = [text[max(m.start() - 200, 0):m.end() + 200] for m in re.finditer(pat, text)]
        if not any(NOTE_WORDS.search(w) and re.search(r"3\.0|\bv3\b|SDK 3", w) for w in windows):
            missing.append(sym)
    return ("fail", f"not surfaced with its 3.0 change: {missing}") if missing else ("pass", "surfaced")


def a_removed_plainly(c, t):
    if not c["plain_removed"]:
        return "n/a", "not a removed-API case"
    return ("pass", "said plainly") if PLAIN.search(t["answer_text"]) else ("fail", "never says it no longer exists")


def a_answered(c, t):
    out = t.get("output")
    text = (out or {}).get("answer", "") if out else "I don't know"
    refused = bool(REFUSAL.search(text)) or not out
    if c["expect"] == "answer":
        return ("fail", "refused / no output") if (not out or text.startswith("I don't know")) else ("pass", "answered")
    return ("pass", "declined correctly") if refused else ("fail", "answered something the docs do not cover")


def a_facts(c, t):
    if not c["must_include"]:
        return "n/a", "no facts"
    body = t["answer_text"]
    missing = [p for p in c["must_include"] if not re.search(p, body, re.I)]
    return ("fail", f"missing /{missing[0]}/") if missing else ("pass", "present")


def a_pii_never_logged(c, t):
    if not c["pii"]:
        return "n/a", "no secrets in the question"
    leaks = []
    blobs = [t["answer_text"], json.dumps(t)]
    for f in LOG_DIR.glob("*.jsonl"):
        blobs.append(f.read_text())
    for secret in c["pii"]:
        if any(secret in b for b in blobs):
            leaks.append(secret[:6] + "...")
    return ("fail", f"secret found in logs/trace: {leaks}") if leaks else ("pass", f"{len(c['pii'])} secret(s) absent everywhere")


ASSERTIONS = {
    "version_resolved": a_version_resolved,
    "code_presence": a_code_presence,
    "code_parses": a_code_parses,
    "code_runs_on_version": a_code_runs_on_version,
    "code_must_not": a_code_must_not,
    "cites_version": a_cites_version,
    "citations_grounded": a_citations_grounded,
    "deprecation_surfaced": a_deprecation_surfaced,
    "removed_said_plainly": a_removed_plainly,
    "answered_when_answerable": a_answered,
    "required_facts_present": a_facts,
    "pii_never_logged": a_pii_never_logged,
}


def run_assertions(case: dict, trace: dict) -> dict:
    return {name: list(fn(case, trace)) for name, fn in ASSERTIONS.items()}


# ---------------------------------------------------------------- trajectory (Week 8 method, Week 12 tools)

def _matches(m: dict, call: dict) -> bool:
    if call["tool"] != m["tool"] or call.get("isError"):
        return False
    args, res = call.get("args") or {}, call.get("result") if isinstance(call.get("result"), dict) else {}
    if "version" in m:
        raw = str(args.get("sdk_version", args.get("api_version", "")))  # r0's Week 9 server calls it api_version
        mm = g._major_minor(raw if raw.lower().startswith("v") else f"v{raw}")
        if not mm or mm[0] != m["version"]:
            return False
    if "page" in m and not any(r.get("chunk_id", "").startswith(m["page"]) for r in res.get("results", [])):
        return False
    if "symbol" in m and g._norm(args.get("symbol", "")).split(".")[-1] != m["symbol"].lower():
        return False
    if "path" in m and str(args.get("path", "")).rstrip("/") != m["path"]:
        return False
    return True


def covered(paths: list[list[dict]], calls: list[dict]) -> str | None:
    for path in paths:
        used: set[int] = set()
        for m in path:
            hit = next((i for i, c in enumerate(calls) if i not in used and _matches(m, c)), None)
            if hit is None:
                break
            used.add(hit)
        else:
            return " + ".join(f"{m['tool']}({m.get('page') or m.get('symbol') or m.get('path') or m.get('version')})"
                              for m in path)
    return None


def score_trajectory(case: dict, trace: dict, outcome_pass: bool) -> dict | None:
    if "paths" not in case:
        return None
    calls = trace["tool_calls"]
    laps = [s for s in trace["spans"] if s["name"] == "agent.lap"]
    action = [s for s in laps if s.get("action") not in ("final", None)]
    tools_ok = set(case["tools_ok"])
    path = covered(case["paths"], calls)
    fails = [] if path else ["no accepted path covered"]
    fails += [f"wrong tool {c['tool']}" for c in calls if c["tool"] not in tools_ok]
    fails += [f"{c['tool']}: model sent sdk_version={c['enforced']['from']!r}, host pinned {c['enforced']['to']!r}"
              for c in calls if c.get("enforced")]
    fails += [f"{c['tool']} error" for c in calls if c.get("isError")]
    seen = Counter((c["tool"], json.dumps(c["args"], sort_keys=True)) for c in calls)
    if sum(n - 1 for n in seen.values()):
        fails.append("repeated identical call")
    optimal = min(len(p) for p in case["paths"]) + 1
    if trace["llm_calls"] > 2 * optimal + trace.get("repairs", 0):
        fails.append(f"{trace['llm_calls']} laps vs {optimal} optimal")
    if trace["status"] != "done":
        fails.append(f"status {trace['status']}")
    return {"trajectory_pass": not fails, "fails": fails, "covered_path": path, "outcome_pass": outcome_pass,
            "tool_choice": [sum(1 for s in action if s["action"] in tools_ok), len(action)],
            "path_str": " ".join(s.get("action", "?")[:6] for s in laps), "laps": trace["llm_calls"],
            "optimal": optimal}


# ---------------------------------------------------------------- running a release

def slim(trace: dict) -> dict:
    return {k: trace[k] for k in ("trace_id", "release", "status", "version", "answer_text", "output", "code_check",
                                  "notes", "citations", "dropped_citations", "withheld", "repairs", "llm_calls",
                                  "tokens", "cost_usd", "latency_ms", "trace_propagation", "spans", "redactions")} | {
        "tool_calls": [{k: c.get(k) for k in ("tool", "args", "args_sent", "enforced", "isError", "result")}
                       for c in trace["tool_calls"]]}


async def _run(release: str, cases: list[dict], label: str) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)
    async with Engine(release, label=label) as eng:
        async def one(case):
            async with sem:
                trace = await eng.ask(case["question"], case["sdk_version"], case_id=case["id"])
                res = run_assertions(case, trace)
                outcome = all(s != "fail" for s, _ in res.values())
                # the eval's own files follow the product's rule: redact on write (seam S21)
                row = {"case_id": case["id"], "mode": case["mode"], "question": g.redact(case["question"])[0],
                       "sdk_version": case["sdk_version"], "assertions": res, "outcome_pass": outcome,
                       "trajectory": score_trajectory(case, trace, outcome), "trace": slim(trace)}
                print(f"  {case['id']} {'PASS' if outcome else 'FAIL'} {trace['trace_id']} "
                      f"${trace['cost_usd']:.4f} {trace['latency_ms'] / 1000:.1f}s "
                      f"{'; '.join(f'{n}: {d}' for n, (s, d) in res.items() if s == 'fail')[:150]}", flush=True)
                return row
        return await asyncio.gather(*(one(c) for c in cases))


def cmd_run(release: str, label: str, ids: list[str] | None) -> list[dict]:
    cases = load_cases(ids)
    print(f"running {len(cases)} cases on release {release} ({RELEASES[release]['config'].name}) -> runs/{label}.jsonl")
    rows = asyncio.run(_run(release, cases, label))
    rows.sort(key=lambda r: r["case_id"])
    RUNS.mkdir(parents=True, exist_ok=True)
    if not ids:
        (RUNS / f"{label}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print_summary(label, rows)
    return rows


def load_run(label: str) -> list[dict]:
    return [json.loads(l) for l in (RUNS / f"{label}.jsonl").read_text().splitlines() if l.strip()]


# ---------------------------------------------------------------- metrics

def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else "-"


def wrong_version_rate(rows: list[dict]) -> tuple[int, int]:
    with_code = [r for r in rows if r["assertions"]["code_runs_on_version"][0] != "n/a"]
    return sum(r["assertions"]["code_runs_on_version"][0] == "fail" for r in with_code), len(with_code)


def looks_like_code_red(rows: list[dict]) -> tuple[int, int]:
    """Bonus: answers whose code passes the Week 6 bar (parses) but fails the symbol-table check."""
    parsed = [r for r in rows if r["assertions"]["code_parses"][0] == "pass"]
    return sum(r["assertions"]["code_runs_on_version"][0] == "fail" for r in parsed), len(parsed)


def trajectory_numbers(rows: list[dict]) -> dict:
    tr = [r["trajectory"] for r in rows if r.get("trajectory")]
    tc = [sum(t["tool_choice"][0] for t in tr), sum(t["tool_choice"][1] for t in tr)]
    out = sum(t["outcome_pass"] for t in tr)
    traj = sum(t["trajectory_pass"] for t in tr)
    # evidence-only: an accepted path covered with the version the MODEL chose, and a final answer; the Week 8
    # efficiency rule (laps <= 2x optimal) is left out, so the two numbers separate "wrong path" from "long path"
    evidence = sum(1 for t in tr if t["covered_path"] and not any("pinned" in f or "status" in f or "error" in f
                                                                  or "wrong tool" in f for f in t["fails"]))
    return {"n": len(tr), "tool_choice": tc, "outcome": out, "trajectory": traj, "evidence": evidence,
            "evidence_gap_pts": round(100 * (out - evidence) / len(tr), 1) if tr else 0.0,
            "mean_laps": round(statistics.mean(t["laps"] for t in tr), 2) if tr else 0,
            "mean_optimal": round(statistics.mean(t["optimal"] for t in tr), 2) if tr else 0,
            "gap_pts": round(100 * (out - traj) / len(tr), 1) if tr else 0.0,
            "right_answer_wrong_path": [r["case_id"] for r in rows if r.get("trajectory")
                                        and r["trajectory"]["outcome_pass"] and not r["trajectory"]["trajectory_pass"]]}


def cost_numbers(rows: list[dict]) -> dict:
    costs = sorted(r["trace"]["cost_usd"] for r in rows)
    lat = sorted(r["trace"]["latency_ms"] for r in rows)
    laps = [r["trace"]["llm_calls"] for r in rows]

    def q(xs, p):
        return xs[min(len(xs) - 1, round(p * (len(xs) - 1)))]
    return {"mean_cost": statistics.mean(costs), "p50_cost": q(costs, .5), "max_cost": costs[-1],
            "p50_ms": q(lat, .5), "p95_ms": q(lat, .95), "max_ms": lat[-1], "mean_laps": statistics.mean(laps),
            "tokens_mean": statistics.mean(r["trace"]["tokens"] for r in rows)}


def rescore_trajectory(rows: list[dict]) -> list[dict]:
    """Trajectory is re-scored from the stored trace, so a matcher fix never needs new model calls."""
    cases = {c["id"]: c for c in load_cases()}
    for r in rows:
        r["trajectory"] = score_trajectory(cases[r["case_id"]], r["trace"], r["outcome_pass"])
    return rows


def print_summary(label: str, rows: list[dict]) -> None:
    rows = rescore_trajectory(rows)
    n = len(rows)
    print(f"\n== {label}: {n} cases, outcome (all assertions) {pct(sum(r['outcome_pass'] for r in rows), n)}")
    by = defaultdict(list)
    for r in rows:
        by[r["mode"]].append(r)
    for m, rs in sorted(by.items()):
        print(f"   {m} {MODES[m][:70]:70} {pct(sum(r['outcome_pass'] for r in rs), len(rs)):>14}")
    print(f"\n   {'assertion':26} applies  fails")
    for name in ASSERTIONS:
        st = [r["assertions"][name][0] for r in rows]
        print(f"   {name:26} {sum(s != 'n/a' for s in st):>7} {st.count('fail'):>6}")
    w, wn = wrong_version_rate(rows)
    red, parsed = looks_like_code_red(rows)
    print(f"\n   WRONG-VERSION CODE RATE: {pct(w, wn)} of answers with code fail the caller's symbol table")
    print(f"   'looks like code' -> red: {red} of {parsed} samples that PARSE fail the symbol-table check")
    t = trajectory_numbers(rows)
    print(f"   trajectory (n={t['n']}): tool-choice {pct(*t['tool_choice'])}, outcome {pct(t['outcome'], t['n'])}, "
          f"trajectory {pct(t['trajectory'], t['n'])}, gap {t['gap_pts']:+.1f} pts; right answer / wrong path: "
          f"{t['right_answer_wrong_path']}")
    print(f"     evidence-only path {pct(t['evidence'], t['n'])}, gap {t['evidence_gap_pts']:+.1f} pts; laps "
          f"{t['mean_laps']} taken vs {t['mean_optimal']} optimal")
    prop = [r["trace"]["trace_propagation"]["all_match"] for r in rows if r["trace"]["trace_propagation"]["mcp_calls"]]
    print(f"   trace id survived every MCP hop: {pct(sum(prop), len(prop))} of traces with an MCP call")
    c = cost_numbers(rows)
    print(f"   cost/question mean ${c['mean_cost']:.5f} p50 ${c['p50_cost']:.5f} max ${c['max_cost']:.5f}; latency "
          f"p50 {c['p50_ms'] / 1000:.1f}s p95 {c['p95_ms'] / 1000:.1f}s; {c['mean_laps']:.2f} LLM calls/question")
    if (LABELS / f"judge_{label}.json").exists() and (LABELS / f"lock_{label}.json").exists():
        agreement(label, rows)


# ---------------------------------------------------------------- judge (Week 6 judge_v2) + hand labels

def judge_context(trace: dict) -> list[dict]:
    out, rank = [], 1
    for c in trace["tool_calls"]:
        res = c["result"] if isinstance(c["result"], dict) else {}
        for r in res.get("results", []) or []:
            out.append({"rank": rank, "chunk_id": r["chunk_id"], "sdk_version": r.get("sdk_version") or r["chunk_id"].split("-")[0],
                        "text": r["text"]})
            rank += 1
        if c["tool"] != "search_docs" and res:
            out.append({"rank": rank, "chunk_id": f"{c['tool']}({json.dumps(c['args'])})",
                        "sdk_version": res.get("sdk_version", "-"), "text": json.dumps(res)[:1200]})
            rank += 1
    return out


def judge_question(row: dict) -> str:
    v = row["trace"]["version"]
    return g.redact(row["question"])[0] + (f"\n(The caller's installed SDK version, sent by their IDE: {row['sdk_version']}.)"
                              if row["sdk_version"] else "") + (f"\n(Resolved: SDK {v['minor']}.)")


def answers_fingerprint(rows: list[dict]) -> str:
    return sha(json.dumps({r["case_id"]: r["trace"]["answer_text"] for r in rows}, sort_keys=True))


def cmd_sheet(label: str) -> None:
    from week6_eval import render_context
    rows = load_run(label)
    order = random.Random(20261027).sample([r["case_id"] for r in rows], len(rows))
    by = {r["case_id"]: r for r in rows}
    lines = [f"# Blind labelling sheet: run `{label}` ({len(rows)} integrated-system answers)", "",
             "**Criterion: DIRECTLY ANSWERS** (the Week 6 wording, unchanged, `week6/judge_v2.txt`).", "",
             "- PASS: a developer on the stated SDK version could act on this answer alone; it states the fact, value, "
             "behaviour or usage they asked for, correct according to the documentation shown.",
             "- FAIL: quotes nearby text that doesn't answer, answers a different question, or says it can't answer "
             "when the documentation shown contains the answer. A decline is PASS only if the docs shown really lack it.",
             "- Ignore code formatting, version labels, deprecation notes, citations: assertions check those.", "",
             "Shuffled order; modes hidden; no judge output exists for this run yet.", ""]
    for i, cid in enumerate(order, 1):
        r = by[cid]
        lines += [f"---\n\n## {i}. `{cid}`: {judge_question(r)}", "", "<details><summary>documentation shown</summary>",
                  "", "```", render_context(judge_context(r["trace"])) or "(no tool results)", "```", "</details>", "",
                  "**Answer:**", "", "```text", r["trace"]["answer_text"], "```", ""]
    LABELS.mkdir(parents=True, exist_ok=True)
    (LABELS / f"sheet_{label}.md").write_text("\n".join(lines))
    lab = LABELS / f"labels_{label}.json"
    if not lab.exists():
        lab.write_text(json.dumps({"run": label, "criterion": "DIRECTLY ANSWERS", "labeler": "",
                                   "answers_sha256": answers_fingerprint(rows),
                                   "labels": [{"id": cid, "label": None, "note": ""} for cid in sorted(by)]}, indent=2))
    print(f"wrote {LABELS / f'sheet_{label}.md'} and {lab}")


def cmd_lock(label: str) -> None:
    rows = load_run(label)
    lab = LABELS / f"labels_{label}.json"
    data = json.loads(lab.read_text())
    bad = [x["id"] for x in data["labels"] if x["label"] not in ("PASS", "FAIL")]
    if bad:
        sys.exit(f"unlabelled: {bad}")
    if data["answers_sha256"] != answers_fingerprint(rows):
        sys.exit("answers changed since the sheet was written; relabel")
    if (LABELS / f"judge_{label}.json").exists():
        sys.exit("a judge run already exists for this run, so these labels cannot be blind")
    lock = {"labels_sha256": sha(lab.read_bytes()), "answers_sha256": data["answers_sha256"], "locked_at_utc": now(),
            "counts": dict(Counter(x["label"] for x in data["labels"]))}
    (LABELS / f"lock_{label}.json").write_text(json.dumps(lock, indent=2))
    print(json.dumps(lock, indent=2))


LABELLED_RUN = "r2_b"  # the run whose answers carry locked hand labels; agreement is measured there


def cmd_judge(label: str, unlabelled_ok: bool = False) -> None:
    from week6_eval import call_judge, load_prompt, render_context
    rows = load_run(label)
    lock_f = LABELS / f"lock_{label}.json"
    if lock_f.exists():
        lock = json.loads(lock_f.read_text())
        if sha((LABELS / f"labels_{label}.json").read_bytes()) != lock["labels_sha256"]:
            sys.exit("labels changed after locking")
    elif unlabelled_ok:  # a fresh run: judge it for the gate, report agreement from the labelled run
        lock = {"labels_sha256": None, "answers_sha256": answers_fingerprint(rows)}
    else:
        sys.exit(f"BLIND PROTOCOL: labels for {label} are not locked; run `sheet`, label, then `lock-labels` first")
    template, fewshot = load_prompt("v2")
    prompts = {r["case_id"]: template.replace("{question}", judge_question(r))
               .replace("{context}", render_context(judge_context(r["trace"])))
               .replace("{answer}", r["trace"]["answer_text"]) for r in rows}
    with ThreadPoolExecutor(4) as pool:
        verdicts = dict(zip(prompts, pool.map(lambda cid: call_judge(prompts[cid]), prompts)))
    (LABELS / f"judge_{label}.json").write_text(json.dumps(
        {"run": label, "judge": "week6/judge_v2.txt", "prompt_sha256": sha(template), "judged_at_utc": now(),
         "labels_sha256": lock["labels_sha256"], "answers_sha256": lock["answers_sha256"], "verdicts": verdicts},
        indent=2))
    if lock["labels_sha256"]:
        agreement(label, rows)
        return
    gate = [r for r in rows if r["outcome_pass"] and verdicts[r["case_id"]]["verdict"] == "PASS"]
    print(f"\n   judge_v2 PASS {sum(v['verdict'] == 'PASS' for v in verdicts.values())}/{len(rows)}; gate (all assertions "
          f"AND judge PASS) {pct(len(gate), len(rows))}. {label} has no hand labels: judge agreement is measured on "
          f"{LABELLED_RUN}:")
    if (LABELS / f"judge_{LABELLED_RUN}.json").exists():
        agreement(LABELLED_RUN, load_run(LABELLED_RUN))


def agreement(label: str, rows: list[dict]) -> dict:
    labels = {x["id"]: x["label"] for x in json.loads((LABELS / f"labels_{label}.json").read_text())["labels"]}
    verdicts = json.loads((LABELS / f"judge_{label}.json").read_text())["verdicts"]
    pairs = [(cid, labels[cid], verdicts[cid]["verdict"]) for cid in sorted(labels)]
    agree = sum(h == j for _, h, j in pairs)
    grid = Counter((h, j) for _, h, j in pairs)
    print(f"\n   JUDGE AGREEMENT (week6 judge_v2 vs hand labels, run {label}): {pct(agree, len(pairs))}  "
          f"{'clears' if agree / len(pairs) >= .85 else 'BELOW'} the 85% bar")
    print(f"     human PASS/judge PASS {grid['PASS', 'PASS']}  human PASS/judge FAIL {grid['PASS', 'FAIL']}  "
          f"human FAIL/judge PASS {grid['FAIL', 'PASS']}  human FAIL/judge FAIL {grid['FAIL', 'FAIL']}")
    for cid, h, j in pairs:
        if h != j:
            print(f"     DISAGREE {cid}: human={h} judge={j}: {verdicts[cid]['reason'][:160]}")
    gate = [r for r in rows if r["outcome_pass"] and verdicts.get(r["case_id"], {}).get("verdict") == "PASS"]
    print(f"     gate (all assertions AND judge PASS): {pct(len(gate), len(rows))}")
    return {"agree": agree, "n": len(pairs), "grid": dict(grid)}


# ---------------------------------------------------------------- one case, RED / GREEN

def cmd_case(case_id: str, release: str) -> int:
    rows = asyncio.run(_run(release, load_cases([case_id]), f"case_{case_id}_{release}"))
    r = rows[0]
    print(f"\n{case_id} on {release}: {'GREEN' if r['outcome_pass'] else 'RED'}  (trace {r['trace']['trace_id']})")
    for name, (s, d) in r["assertions"].items():
        if s != "n/a":
            print(f"   {'ok ' if s == 'pass' else 'RED'} {name:26} {d}")
    print("\n" + r["trace"]["answer_text"])
    return 0 if r["outcome_pass"] else 1


def cmd_rescore(label: str) -> None:
    """Re-run the assertions on a stored run (no model calls) after an assertion fix; prints what flipped."""
    cases = {c["id"]: c for c in load_cases()}
    rows = load_run(label)
    for r in rows:
        new = run_assertions(cases[r["case_id"]], r["trace"])
        flips = [f"{n}: {r['assertions'][n][0]}->{new[n][0]}" for n in new if new[n][0] != r["assertions"][n][0]]
        if flips:
            print(f"  {label} {r['case_id']}: {', '.join(flips)}")
        r["assertions"], r["outcome_pass"] = new, all(s != "fail" for s, _ in new.values())
    (RUNS / f"{label}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["run", "sheet", "lock-labels", "judge", "summary", "case", "rescore"])
    p.add_argument("case_id", nargs="?")
    p.add_argument("--release", default="r2", choices=sorted(RELEASES))
    p.add_argument("--label")
    p.add_argument("--run")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--unlabelled-ok", action="store_true")
    a = p.parse_args()
    if a.cmd == "run":
        cmd_run(a.release, a.label or f"{a.release}_{datetime.now().strftime('%m%d%H%M')}", a.ids)
    elif a.cmd == "sheet":
        cmd_sheet(a.run)
    elif a.cmd == "lock-labels":
        cmd_lock(a.run)
    elif a.cmd == "judge":
        cmd_judge(a.run, a.unlabelled_ok)
    elif a.cmd == "summary":
        print_summary(a.run, load_run(a.run))
    elif a.cmd == "rescore":
        cmd_rescore(a.run)
    elif a.cmd == "case":
        sys.exit(cmd_case(a.case_id, a.release))


if __name__ == "__main__":
    main()
