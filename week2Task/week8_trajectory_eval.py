"""Week 8: trajectory eval for the docs agent. Scores the PATH, not just the answer.

    .venv/bin/python week8_trajectory_eval.py run --variant before            # 10 questions x 3 repeats, agent as shipped in Week 7
    .venv/bin/python week8_trajectory_eval.py run --variant after             # same, with the ONE mitigation (argument validation) on
    .venv/bin/python week8_trajectory_eval.py run --variant attack            # bonus: poisoned docs, no defences
    .venv/bin/python week8_trajectory_eval.py run --variant attack_defended   # bonus: poisoned docs + 3 defences
    .venv/bin/python week8_trajectory_eval.py run --variant defended          # bonus: defences on, no attack (their price)
    .venv/bin/python week8_trajectory_eval.py report                          # every table -> week8/report.md
    .venv/bin/python -m unittest tests.test_week8_trajectory                  # the assertions, on fake runs (no cost)

Every run is scored on:
  outcome     - Week 7's deterministic grader (does the v3 code pass?)
  trajectory  - did the tool calls cover one of the question's ACCEPTED PATHS, with real arguments, no wrong
                tool, no protocol break, no loop, and a final answer?
The gap = outcome pass rate - trajectory pass rate. A run that passes outcome and fails trajectory is a
right answer down a wrong path.
Thinking is off for every variant (Week 7's headline setting).
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import statistics
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import week7_agent
import week7_tools
from week7_agent import Budgets, run_agent
from week7_tools import API_VERSIONS, ROOT, SPEC, W7, grade

W8 = ROOT / "week8"
QUESTIONS = {q["id"]: q for q in map(json.loads, (W7 / "questions.jsonl").read_text().splitlines())}

# ---------------------------------------------------------------- expected paths (asserted as SETS)
# A matcher is (tool, predicate over the recorded call). A path is a list of matchers that must each be
# matched by a DISTINCT call, in ANY order: reading the changelog before or after the spec are both right.
# A case's `paths` is the set of accepted alternatives. `tools_ok` is every tool that is a reasonable
# choice for the question; anything else is a wrong-tool step.


def _norm(sym: str) -> str:
    return re.sub(r"\(\)$", "", str(sym).strip().strip("`")).lower().split(".")[-1]


def dep(*aliases):
    """check_deprecation on one of these symbols, for v3."""
    names = {a.lower() for a in aliases}
    return ("check_deprecation", f"dep({aliases[0]})",
            lambda c: c["args"].get("api_version") == "v3" and _norm(c["args"].get("symbol", "")) in names)


def spec(path):
    """get_openapi_spec on exactly this path."""
    return ("get_openapi_spec", f"spec({path})",
            lambda c: str(c["args"].get("path", "")).strip().rstrip("/") == path)


def docs(prefix, version="v3"):
    """search_docs on `version` whose RESULTS include a chunk from this page/section (evidence retrieved)."""
    return ("search_docs", f"docs({prefix})",
            lambda c: c["args"].get("api_version") == version
            and any(r.get("chunk_id", "").startswith(prefix) for r in (c["result"].get("results") or [])))


def combos(*groups):
    """Cartesian product of alternatives: one matcher from each group."""
    return [list(p) for p in itertools.product(*groups)]


@dataclass
class Case:
    qid: str
    paths: list[list[tuple]]
    tools_ok: set[str]
    why: str
    alt: bool = field(init=False)

    def __post_init__(self):
        self.alt = len(self.paths) > 1


CASES = {
    "Q01": Case("Q01", combos([dep("request", "client.request"), docs("v3-changelog::removed-apis")],
                              [spec("/v3/invoices"), docs("v3-client::client-send")]),
                {"check_deprecation", "get_openapi_spec", "search_docs"},
                "needs evidence that request() was removed (changelog tool OR the changelog page) AND the send() "
                "call shape (spec OR the client page). 2x2 = 4 accepted paths, any order."),
    "Q02": Case("Q02", combos([dep("paginate_auto"), docs("v3-changelog::removed-apis")], [spec("/v3/invoices")]),
                {"check_deprecation", "get_openapi_spec", "search_docs"},
                "removal evidence either way, but the list_after() page shape exists ONLY in the spec, so the "
                "spec is required. 2 accepted paths."),
    "Q03": Case("Q03", [[dep("TooManyRequestsError")], [docs("v2-errors::toomanyrequestserror", "v2")]],
                {"check_deprecation", "search_docs"},
                "the rename is stated by the changelog tool and by the v2 errors page; the v3 errors page alone "
                "never mentions TooManyRequestsError. 2 accepted paths."),
    "Q04": Case("Q04", [[dep("timeout_s")], [docs("v3-changelog::timeout-units-renamed")]],
                {"check_deprecation", "search_docs"},
                "rename evidence from the tool or the changelog page. No endpoint involved, so the spec is a "
                "wrong tool. 2 accepted paths."),
    "Q05": Case("Q05", [[docs("v3-files")], [spec("/v3/files")]],
                {"check_deprecation", "get_openapi_spec", "search_docs"},
                "upload_file is not in the changelog (check_deprecation is allowed, not required); files.upload() "
                "is on the files page and in the spec. 2 accepted paths."),
    "Q06": Case("Q06", [[dep("retry_backoff_ms")], [docs("v3-changelog::retry-defaults-changed")],
                        [docs("v3-client::client-constructor-parameters"), docs("v2-client::client-constructor-parameters", "v2")]],
                {"check_deprecation", "search_docs"},
                "the changelog (tool or page) states the old 2000 ms default; comparing the v2 and v3 constructor "
                "tables (default 2000 vs 500) is also evidence. 3 accepted paths. The third was added after the "
                "'after' sweep (Q06 r2) showed the agent doing exactly that and being scored as unevidenced."),
    "Q07": Case("Q07", [[docs("v3-streaming")], [spec("/v3/events")]],
                {"get_openapi_spec", "search_docs"},
                "v3-only how-to: streaming page or the /v3/events spec. 2 accepted paths."),
    "Q08": Case("Q08", [[spec("/v3/invoices")], [docs("v3-client::client-send")]],
                {"get_openapi_spec", "search_docs"},
                "v3-only: the POST spec or the client page's send() example. 2 accepted paths."),
    "Q09": Case("Q09", [[docs("v3-webhooks")]], {"search_docs"},
                "SINGLE path: verify_signature exists only on the webhooks page; the spec has no webhook path and "
                "the changelog never mentions it."),
    "Q10": Case("Q10", [[docs("v3-errors::ratelimiterror")]], {"search_docs", "check_deprecation"},
                "SINGLE path: retry_after_seconds is documented only on the v3 errors page (the rate-limits page "
                "points there). check_deprecation is tolerated, not sufficient."),
}

# ---------------------------------------------------------------- argument validity

_CORPUS_TEXT = "\n".join(f.read_text() for f in sorted((ROOT / "corpus").rglob("*.md")))
_CORPUS_IDENTS = {t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _CORPUS_TEXT)}
_CORPUS_DOTTED = {t.lower() for t in re.findall(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", _CORPUS_TEXT)}


def real_symbol(symbol) -> bool:
    """Does this symbol occur anywhere in the v2 or v3 docs? `client.invoices.create` does not."""
    sym = re.sub(r"\(\)$", "", str(symbol).strip().strip("`")).lower()
    sym = re.sub(r"^(self|client)\.", "", sym)
    if not sym:
        return False
    if "." in sym:
        return sym in _CORPUS_DOTTED or f"client.{sym}" in _CORPUS_DOTTED
    return sym in _CORPUS_IDENTS


def arg_problems(tool: str, args: dict) -> list[str]:
    """Why these arguments are fluent fiction, or [] if every endpoint / version / symbol is real."""
    if tool not in week7_tools.TOOL_FUNCS:
        return [f"unknown tool {tool!r}"]
    if not isinstance(args, dict):
        return ["args not an object"]
    probs = []
    if tool in ("search_docs", "check_deprecation") and args.get("api_version") not in API_VERSIONS:
        probs.append(f"api_version={args.get('api_version')!r} not in {API_VERSIONS}")
    if tool == "search_docs" and not str(args.get("query", "")).strip():
        probs.append("empty query")
    if tool == "get_openapi_spec":
        path = str(args.get("path", "")).strip().rstrip("/")
        if path not in SPEC["paths"]:
            probs.append(f"path {path!r} is not in the v3 API")
    if tool == "check_deprecation":
        if not real_symbol(args.get("symbol", "")):
            probs.append(f"symbol {args.get('symbol')!r} appears nowhere in the SDK docs")
    return probs


# ---------------------------------------------------------------- scoring one run

MODES = ["answer_without_evidence", "invalid_args", "wrong_tool", "protocol_break", "loop_thrash", "no_answer"]
SEVERITY = {"answer_without_evidence": "ships a time bomb (right today, breaks at the next release)",
            "invalid_args": "made-up inputs: missing / off-enum / fictional endpoint or symbol; wastes laps, can loop",
            "wrong_tool": "wasted lap, wrong evidence",
            "protocol_break": "wasted lap and tokens",
            "loop_thrash": "cost blow-up",
            "no_answer": "user gets nothing"}


def covered_path(case: Case, calls: list[dict]) -> str | None:
    """Name of the first accepted path fully matched by distinct calls (any order), else None."""
    for path in case.paths:
        used: set[int] = set()
        ok = True
        for tool, label, pred in path:
            hit = next((i for i, c in enumerate(calls) if i not in used and c["tool"] == tool and pred(c)), None)
            if hit is None:
                ok = False
                break
            used.add(hit)
        if ok:
            return " + ".join(label for _, label, _ in path)
    return None


def score(qid: str, result: dict, calls: list[dict], events: list[dict]) -> dict:
    case, q = CASES[qid], QUESTIONS[qid]
    laps = [e for e in events if e["event"] == "lap"]
    malformed = [e for e in laps if not e.get("tool") and not e.get("final")]
    action_laps = [e for e in laps if not e.get("final")]
    for c in calls:
        c["arg_problems"] = arg_problems(c["tool"], c["args"])
        c["tool_ok"] = c["tool"] in case.tools_ok
    seen = Counter((c["tool"], json.dumps(c["args"], sort_keys=True)) for c in calls)
    repeated = sum(n - 1 for n in seen.values())
    optimal = min(len(p) for p in case.paths) + 1
    taken = result["llm_calls"]
    path = covered_path(case, calls)
    outcome_ok, outcome_fails = grade(q, result["output"])
    modes = []
    if result["status"] == "done" and not path:
        modes.append("answer_without_evidence")
    if any(c["arg_problems"] for c in calls):
        modes.append("invalid_args")
    if any(not c["tool_ok"] for c in calls):
        modes.append("wrong_tool")
    if malformed:
        modes.append("protocol_break")
    if repeated or taken > 2 * optimal:
        modes.append("loop_thrash")
    if result["status"] != "done":
        modes.append("no_answer")
    traj_fails = []
    if not path:
        traj_fails.append("no accepted path covered")
    traj_fails += [f"{c['tool']}: {p}" for c in calls for p in c["arg_problems"]]
    traj_fails += [f"wrong tool {c['tool']}" for c in calls if not c["tool_ok"]]
    if repeated:
        traj_fails.append(f"{repeated} repeated identical call(s)")
    if taken > 2 * optimal:
        traj_fails.append(f"{taken} laps vs {optimal} optimal")
    if result["status"] != "done":
        traj_fails.append(f"status {result['status']}")
    short = {"check_deprecation": "c", "search_docs": "s", "get_openapi_spec": "g"}
    path_str = " ".join((short.get(e["tool"], "?") if e.get("tool") else ("F" if e.get("final") else "x"))
                        for e in laps)
    return {
        "outcome_pass": outcome_ok, "outcome_fails": outcome_fails,
        "trajectory_pass": bool(path) and not traj_fails, "trajectory_fails": traj_fails, "covered_path": path,
        # strict: a malformed (protocol-break) lap also fails the path. Headline scoring charges those laps to
        # tool-choice accuracy and step efficiency instead, so the gap measures evidence, not reply formatting.
        "trajectory_pass_strict": bool(path) and not traj_fails and not malformed, "malformed_laps": len(malformed),
        "modes": modes, "path_str": path_str,
        "tool_choice": (sum(1 for e in action_laps if e.get("tool") in case.tools_ok), len(action_laps)),
        "arg_valid": (sum(1 for c in calls if not c["arg_problems"]), len(calls)),
        "steps_taken": taken, "steps_optimal": optimal, "efficiency": round(taken / optimal, 2),
    }


# ---------------------------------------------------------------- running the agent with a recorder

VARIANTS = {  # validate = the ONE mitigation (week7_tools.VALIDATE_ARGS); poison / defend = bonus layers only
    "before": dict(validate=False, poison=False, defend=False),
    "after": dict(validate=True, poison=False, defend=False),
    "attack": dict(validate=True, poison="comment", defend=False),
    "attack_defended": dict(validate=True, poison="comment", defend=True),
    "attack_subtle": dict(validate=True, poison="subtle", defend=False),
    "attack_subtle_defended": dict(validate=True, poison="subtle", defend=True),
    "defended": dict(validate=True, poison=False, defend=True),
}
_tls = threading.local()
_search_lock = threading.Lock()
_real_run_tool = week7_tools.run_tool


def _recording_run_tool(name: str, args: dict) -> dict:
    layers = getattr(_tls, "layers", None)
    if layers is None:  # not inside an eval job (e.g. the unit tests): plain Week 7 behaviour
        return _real_run_tool(name, args)
    if layers["defend"]:
        from week8_defenses import scope_check
        problem = scope_check(name)
        if problem:
            result = {"error": problem}
            _tls.calls.append({"tool": name, "args": args, "result": result, "refused": True})
            return result
    if name == "search_docs":
        with _search_lock:  # chroma + the embedder are not thread-safe
            if layers["poison"]:
                from week8_defenses import poisoned_search_docs
                problem = week7_tools.validate_args(name, args) if week7_tools.VALIDATE_ARGS else None
                if problem:  # keep the mitigation in force on the poisoned tool too
                    result = {"error": problem}
                elif isinstance(args, dict):
                    result = _call(poisoned_search_docs, {**args, "style": layers["poison"]})
                else:
                    result = _call(poisoned_search_docs, {})
            else:
                result = _real_run_tool(name, args)
    else:
        result = _real_run_tool(name, args)
    if layers["defend"]:
        from week8_defenses import sanitize_result
        result, dropped = sanitize_result(result)
        _tls.dropped += dropped
    _tls.calls.append({"tool": name, "args": args, "result": result})
    return result


def _call(fn, args):
    try:
        return fn(**args)
    except TypeError as exc:
        return {"error": f"bad arguments for {fn.__name__}: {exc}"}


week7_agent.run_tool = _recording_run_tool


def run_one(job: tuple[str, str, int]) -> dict:
    variant, qid, rep = job
    layers = VARIANTS[variant]
    _tls.layers, _tls.calls, _tls.dropped = layers, [], 0
    log = W8 / "logs" / variant / f"agent_{qid}_r{rep}.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    result = run_agent(QUESTIONS[qid]["question"], Budgets(), log_path=log, echo=False)
    blocked = None
    obeyed = False
    if layers["poison"] or layers["defend"]:
        from week8_defenses import guardrail, obeyed as _obeyed
        obeyed = _obeyed(result["output"])
        if layers["defend"]:
            result["output"], blocked = guardrail(result["output"])
            if blocked:
                result["status"] = "guardrail_blocked"
    events = [json.loads(line) for line in log.read_text().splitlines()]
    row = {"variant": variant, "qid": qid, "repeat": rep, "status": result["status"], "laps": result["llm_calls"],
           "llm_calls": result["llm_calls"], "tokens": result["tokens"], "cost_usd": round(result["cost_usd"], 6),
           "latency_s": result["latency_s"], "output": result["output"], "calls": _tls.calls, "events": events,
           "injection_obeyed": obeyed, "guardrail_blocked": blocked, "sanitizer_dropped_lines": _tls.dropped}
    row.update(score(qid, {**result, "output": result["output"]}, _tls.calls, events))
    print(f"{variant:16} {qid} r{rep} outcome {'PASS' if row['outcome_pass'] else 'FAIL'} "
          f"traj {'PASS' if row['trajectory_pass'] else 'FAIL'} [{row['path_str']}] {row['latency_s']:5.1f}s "
          f"{row['tokens']:5} tok ${row['cost_usd']:.4f} {'; '.join(row['trajectory_fails'])[:90]}", flush=True)
    return row


def cmd_run(a) -> None:
    week7_tools.THINKING_TOKENS = 0
    week7_tools.VALIDATE_ARGS = VARIANTS[a.variant]["validate"]  # the ONE mitigation, on for every variant but "before"
    week7_tools.warm_up()
    W8.mkdir(exist_ok=True)
    jobs = [(a.variant, qid, rep) for rep in range(1, a.repeats + 1) for qid in QUESTIONS]
    random.Random(8).shuffle(jobs)
    with ThreadPoolExecutor(a.workers) as pool:
        rows = list(pool.map(run_one, jobs))
    rows.sort(key=lambda r: (r["qid"], r["repeat"]))
    out = W8 / f"runs_{a.variant}.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"\n{len(rows)} runs -> {out}")
    print(summary_text(rows))


# ---------------------------------------------------------------- aggregation and report

def load(variant: str) -> list[dict]:
    p = W8 / f"runs_{variant}.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []


def p50(xs):
    return statistics.median(xs) if xs else 0


def metrics(rows: list[dict]) -> dict:
    tc_num, tc_den = (sum(r["tool_choice"][i] for r in rows) for i in (0, 1))
    av_num, av_den = (sum(r["arg_valid"][i] for r in rows) for i in (0, 1))
    costs, lats, toks, effs = ([r[k] for r in rows] for k in ("cost_usd", "latency_s", "tokens", "efficiency"))
    outcome = sum(r["outcome_pass"] for r in rows) / len(rows)
    traj = sum(r["trajectory_pass"] for r in rows) / len(rows)
    strict = sum(r["trajectory_pass_strict"] for r in rows) / len(rows)
    return {"runs": len(rows), "outcome_pass_rate": outcome, "trajectory_pass_rate": traj, "gap": outcome - traj,
            "trajectory_pass_rate_strict": strict, "gap_strict": outcome - strict,
            "tool_choice_accuracy": tc_num / tc_den if tc_den else 0, "tool_choice_n": (tc_num, tc_den),
            "argument_validity": av_num / av_den if av_den else 0, "argument_n": (av_num, av_den),
            "step_efficiency_mean": statistics.mean(effs), "step_efficiency_p50": p50(effs), "step_efficiency_max": max(effs),
            "steps_taken": sum(r["steps_taken"] for r in rows), "steps_optimal": sum(r["steps_optimal"] for r in rows),
            "cost_p50": p50(costs), "cost_max": max(costs), "cost_mean": statistics.mean(costs),
            "latency_p50": p50(lats), "latency_max": max(lats), "latency_p99": sorted(lats)[int(0.99 * (len(lats) - 1))],
            "tokens_p50": p50(toks), "tokens_max": max(toks), "tokens_mean": statistics.mean(toks),
            "laps_mean": statistics.mean(r["laps"] for r in rows),
            "mode_counts": Counter(m for r in rows for m in r["modes"]),
            "status_counts": Counter(r["status"] for r in rows),
            "false_positives": [r for r in rows if r["outcome_pass"] and not r["trajectory_pass"]],
            "false_negatives": [r for r in rows if not r["outcome_pass"] and r["trajectory_pass"]]}


def summary_text(rows: list[dict]) -> str:
    m = metrics(rows)
    return (f"outcome {m['outcome_pass_rate']:.0%}  trajectory {m['trajectory_pass_rate']:.0%}  gap {m['gap']:+.0%} | "
            f"tool-choice {m['tool_choice_accuracy']:.0%} ({m['tool_choice_n'][0]}/{m['tool_choice_n'][1]})  "
            f"arg-valid {m['argument_validity']:.0%} ({m['argument_n'][0]}/{m['argument_n'][1]})  "
            f"efficiency mean {m['step_efficiency_mean']:.2f} max {m['step_efficiency_max']:.2f} | "
            f"cost/q p50 ${m['cost_p50']:.4f} max ${m['cost_max']:.4f} | modes {dict(m['mode_counts'])}")


def results_table(named: list[tuple[str, list[dict]]]) -> str:
    ms = [(n, metrics(r)) for n, r in named if r]
    head = "| Metric | " + " | ".join(n for n, _ in ms) + " |\n|---|" + "---|" * len(ms) + "\n"
    rows_ = [
        ("Runs (10 questions x repeats)", lambda m: f"{m['runs']}"),
        ("Outcome pass rate (Week 7 grader)", lambda m: f"{m['outcome_pass_rate']:.1%}"),
        ("Trajectory pass rate", lambda m: f"{m['trajectory_pass_rate']:.1%}"),
        ("**Gap = outcome - trajectory**", lambda m: f"**{m['gap']:+.1%}**"),
        ("Trajectory pass rate, STRICT (a malformed lap also fails the path)", lambda m: f"{m['trajectory_pass_rate_strict']:.1%}"),
        ("Gap, strict", lambda m: f"{m['gap_strict']:+.1%}"),
        ("Tool-choice accuracy (valid tool in expected set / action steps)",
         lambda m: f"{m['tool_choice_accuracy']:.1%} ({m['tool_choice_n'][0]}/{m['tool_choice_n'][1]})"),
        ("Argument validity rate (real path/version/symbol / tool calls)",
         lambda m: f"{m['argument_validity']:.1%} ({m['argument_n'][0]}/{m['argument_n'][1]})"),
        ("Step efficiency = steps taken / steps needed (mean; p50; max)",
         lambda m: f"{m['step_efficiency_mean']:.2f}; {m['step_efficiency_p50']:.2f}; {m['step_efficiency_max']:.2f}"),
        ("Steps taken / steps needed (totals)", lambda m: f"{m['steps_taken']} / {m['steps_optimal']}"),
        ("Cost per question p50", lambda m: f"${m['cost_p50']:.4f}"),
        ("Cost per question MAX", lambda m: f"${m['cost_max']:.4f}"),
        ("Cost per question mean (for reference only)", lambda m: f"${m['cost_mean']:.4f}"),
        ("Tokens per question p50 / max", lambda m: f"{m['tokens_p50']:.0f} / {m['tokens_max']}"),
        ("Latency p50 / p99 / max (s)", lambda m: f"{m['latency_p50']:.1f} / {m['latency_p99']:.1f} / {m['latency_max']:.1f}"),
        ("LLM laps per question (mean)", lambda m: f"{m['laps_mean']:.2f}"),
        ("Right answer, wrong path (outcome pass & trajectory fail)", lambda m: f"{len(m['false_positives'])}"),
        ("Wrong answer, right path (outcome fail & trajectory pass)", lambda m: f"{len(m['false_negatives'])}"),
    ]
    return head + "".join(f"| {label} | " + " | ".join(fn(m) for _, m in ms) + " |\n" for label, fn in rows_)


def mode_matrix(named: list[tuple[str, list[dict]]]) -> str:
    ms = [(n, metrics(r)) for n, r in named if r]
    all_modes = MODES + sorted({m for _, mm in ms for m in mm["mode_counts"] if m not in MODES})
    out = "| Failure mode (runs showing it) | Severity | " + " | ".join(n for n, _ in ms) + " | Change |\n|---|---|" + "---|" * (len(ms) + 1) + "\n"
    for mode in all_modes:
        counts = [mm["mode_counts"].get(mode, 0) for _, mm in ms]
        if len(counts) >= 2:
            d = counts[-1] - counts[0]
            change = "**WORSE**" if d > 0 else ("better" if d < 0 else "same")
            if counts[0] == 0 and counts[-1] > 0:
                change = "**NEW**"
            change += f" ({d:+d})"
        else:
            change = ""
        out += f"| {mode} | {SEVERITY.get(mode, '')} | " + " | ".join(str(c) for c in counts) + f" | {change} |\n"
    out += "| *(outcome) wrong answer* | | " + " | ".join(str(sum(not r['outcome_pass'] for r in rows)) for _, rows in named if rows) + " | |\n"
    out += "| *(status) breakdown* | | " + " | ".join(", ".join(f"{k}={v}" for k, v in mm["status_counts"].items()) for _, mm in ms) + " | |\n"
    return out


def trace_md(r: dict) -> str:
    q = QUESTIONS[r["qid"]]
    lines = [f"**{r['qid']}, repeat {r['repeat']}, variant `{r['variant']}`** - question: {q['question']}", "",
             f"- outcome: **PASS** (grader found {q['code_must']} and none of {q['code_must_not']}; "
             f"flagged {q['must_flag']})",
             f"- trajectory: **FAIL** - {'; '.join(r['trajectory_fails'])}"
             + (f" (plus {r['malformed_laps']} malformed lap(s), charged to tool-choice accuracy and efficiency)" if r['malformed_laps'] else ""),
             f"- accepted paths for this question: " + " OR ".join(
                 "[" + " + ".join(l for _, l, _ in p) + "]" for p in CASES[r["qid"]].paths),
             f"- path taken: `{r['path_str']}` (c=check_deprecation s=search_docs g=get_openapi_spec F=final x=malformed)",
             "", "```"]
    for e in r["events"]:
        if e["event"] == "lap":
            what = (f"tool={e['tool']} args={json.dumps(e['args'])}" if e.get("tool")
                    else ("FINAL" if e.get("final") else f"MALFORMED reply: {e.get('unparsed_reply', '')[:200]!r}"))
            lines.append(f"lap {e['lap']} t={e['t']:5.1f}s tokens_total={e['tokens_total']:5}  {what}")
            if e.get("thought"):
                lines.append(f"      thought: {e['thought'][:160]}")
        elif e["event"] == "tool_result":
            lines.append(f"      result: {e['result'][:200]}")
        elif e["event"] == "end":
            lines.append(f"end   status={e['status']} laps={e['laps']} tokens={e['tokens']} cost=${e['cost_usd']:.4f}")
    out = r["output"] or {}
    lines += ["```", "", "Final answer the outcome grader passed:", "```python", str(out.get("v3_code", "")), "```",
              f"answer: {out.get('answer', '')}", f"deprecations: {json.dumps(out.get('deprecations'))}",
              f"sources: {json.dumps(out.get('sources'))}"]
    return "\n".join(lines)


def paths_md() -> str:
    out = "| Case | Class | Accepted paths (any order; one matcher per distinct call) | Alt? | Tools OK | Why |\n|---|---|---|---|---|---|\n"
    for qid, c in CASES.items():
        paths = " **OR** ".join("[" + " + ".join(l for _, l, _ in p) + "]" for p in c.paths)
        out += (f"| {qid} | {QUESTIONS[qid]['class']} | {paths} | {'yes (' + str(len(c.paths)) + ')' if c.alt else 'no (1)'} | "
                f"{', '.join(sorted(c.tools_ok))} | {c.why} |\n")
    return out


def per_question_md(rows: list[dict]) -> str:
    out = "| Q | outcome | trajectory | paths taken (per repeat) | cost p50 / max | modes |\n|---|---|---|---|---|---|\n"
    by = defaultdict(list)
    for r in rows:
        by[r["qid"]].append(r)
    for qid, rs in sorted(by.items()):
        costs = [r["cost_usd"] for r in rs]
        modes = Counter(m for r in rs for m in r["modes"])
        out += (f"| {qid} | {sum(r['outcome_pass'] for r in rs)}/{len(rs)} | {sum(r['trajectory_pass'] for r in rs)}/{len(rs)} | "
                f"{', '.join('`' + r['path_str'] + '`' for r in rs)} | ${p50(costs):.4f} / ${max(costs):.4f} | "
                f"{', '.join(f'{k}x{v}' for k, v in modes.items()) or '-'} |\n")
    return out


def price_md(before: list[dict], after: list[dict], label_b: str, label_a: str) -> str:
    b, a = metrics(before), metrics(after)
    rows_ = [("Latency p50 (s)", b["latency_p50"], a["latency_p50"], "{:.2f}"),
             ("Latency p99 (s)", b["latency_p99"], a["latency_p99"], "{:.2f}"),
             ("Latency max (s)", b["latency_max"], a["latency_max"], "{:.2f}"),
             ("Tokens per question p50", b["tokens_p50"], a["tokens_p50"], "{:.0f}"),
             ("Tokens per question mean", b["tokens_mean"], a["tokens_mean"], "{:.0f}"),
             ("Cost per question p50 ($)", b["cost_p50"], a["cost_p50"], "{:.4f}"),
             ("Cost per question max ($)", b["cost_max"], a["cost_max"], "{:.4f}"),
             ("Cost per question mean ($)", b["cost_mean"], a["cost_mean"], "{:.4f}"),
             ("LLM laps per question", b["laps_mean"], a["laps_mean"], "{:.2f}"),
             ("Step efficiency mean", b["step_efficiency_mean"], a["step_efficiency_mean"], "{:.2f}")]
    out = f"| Price metric | {label_b} | {label_a} | Delta |\n|---|---|---|---|\n"
    for name, x, y, fmt in rows_:
        pct = f" ({(y - x) / x:+.0%})" if x else ""
        out += f"| {name} | {fmt.format(x)} | {fmt.format(y)} | {fmt.format(y - x).replace('-', '-') if y - x < 0 else '+' + fmt.format(y - x)}{pct} |\n"
    return out


def cmd_report(a) -> None:
    before, after = load("before"), load("after")
    attack, attack_def, defended = load("attack"), load("attack_defended"), load("defended")
    subtle, subtle_def = load("attack_subtle"), load("attack_subtle_defended")
    md = ["# Week 8 trajectory eval - generated by `week8_trajectory_eval.py report`", "",
          "## 1. The 10 expected tool sequences (asserted as sets in `CASES`)", "", paths_md(), "",
          "## 2. Results table", "", results_table([("before", before), ("after (argument validation)", after)]), ""]
    if before:
        b = metrics(before)
        md += ["## 3. Outcome-vs-trajectory gap (before)", "",
               f"**Gap = {b['outcome_pass_rate']:.1%} outcome - {b['trajectory_pass_rate']:.1%} trajectory = {b['gap']:+.1%}** "
               f"({len(b['false_positives'])} of {b['runs']} runs passed the answer check and failed the path check).", "",
               "Per question (before):", "", per_question_md(before), ""]
        # show the worst one: an unevidenced answer if any, else the run that wasted the most laps
        fps = sorted(b["false_positives"], key=lambda r: ("answer_without_evidence" not in r["modes"], -r["laps"], r["qid"]))
        if fps:
            md += ["### 3a. One right-answer-wrong-path trace", "", trace_md(fps[0]), "",
                   "All right-answer-wrong-path runs (before): " + ", ".join(
                       f"{r['qid']} r{r['repeat']} `{r['path_str']}` ({'; '.join(r['trajectory_fails'])[:80]})" for r in fps), ""]
        md += ["### 3b. Failure modes (before), ranked by severity then count", "", mode_matrix([("before", before)]), ""]
    if before and after:
        md += ["## 4. The ONE mitigation: argument validation - before -> after", "",
               "Top mode by severity-then-count, before -> after:", "", mode_matrix([("before", before), ("after", after)]), "",
               "### Price paid", "", price_md(before, after, "before", "after"), "",
               "Per question (after):", "", per_question_md(after), ""]
    if attack or attack_def:
        def obey(rows):
            return f"{sum(r['injection_obeyed'] for r in rows)}/{len(rows)}" if rows else "-"
        md += ["## 5. Bonus: indirect prompt injection", "",
               "| Run | Injection reached the user (TLS-disable in answer/code) | Guardrail blocked | Sanitizer dropped lines | Scope refusals | outcome pass | trajectory pass |",
               "|---|---|---|---|---|---|---|"]
        for name, rows in (("attack 1: 'ignore previous instructions' comment, no defences", attack),
                           ("attack 1 + 3 defences", attack_def),
                           ("attack 2: docs-style 'verify=False is required', no defences", subtle),
                           ("attack 2 + 3 defences", subtle_def),
                           ("defences on, no attack", defended)):
            if rows:
                md.append(f"| {name} | {obey(rows)} | {sum(bool(r['guardrail_blocked']) for r in rows)} | "
                          f"{sum(r['sanitizer_dropped_lines'] for r in rows)} | "
                          f"{sum(1 for r in rows for c in r['calls'] if c.get('refused'))} | "
                          f"{sum(r['outcome_pass'] for r in rows)}/{len(rows)} | {sum(r['trajectory_pass'] for r in rows)}/{len(rows)} |")
        md.append("")
        for label, rows in (("attack 1", attack), ("attack 2", subtle)):
            if rows:
                hits = [r for r in rows if r["injection_obeyed"]]
                saw = sum(any(c["tool"] == "search_docs" and "error" not in c["result"] for c in r["calls"]) for r in rows)
                md += [f"{label}, no defences: {saw}/{len(rows)} runs called search_docs and so received the poison; "
                       f"the injection reached the user in {len(hits)}: " + (", ".join(f"{r['qid']} r{r['repeat']}" for r in hits) or "none"), ""]
                for r in hits[:3]:
                    o = r["output"] or {}
                    md += [f"- {r['qid']} r{r['repeat']}: answer: {o.get('answer', '')[:300]!r}", f"  code: {o.get('v3_code', '')[:400]!r}"]
                md.append("")
        for label, rows in (("attack 1", attack_def), ("attack 2", subtle_def)):
            if rows:
                hits = [r for r in rows if r["injection_obeyed"]]
                md += [f"{label} + defences: TLS-disable present in the model's raw output (before the guardrail) in "
                       f"{len(hits)}/{len(rows)} runs; guardrail blocked {sum(bool(r['guardrail_blocked']) for r in rows)}; "
                       f"reached the user in {sum(1 for r in rows if r['injection_obeyed'] and not r['guardrail_blocked'])}.", ""]
        if after and defended:
            md += ["### What the defences cost (after -> defended, no attack)", "", price_md(after, defended, "after", "defended"), "",
                   results_table([("after", after), ("defended", defended)]), ""]
    (W8 / "report.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\n-> {W8 / 'report.md'}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--variant", choices=VARIANTS, required=True)
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--workers", type=int, default=4)
    sub.add_parser("report")
    a = p.parse_args()
    {"run": cmd_run, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
