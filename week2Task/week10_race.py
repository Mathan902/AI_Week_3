"""Week 10: race the docs squad (week10_squad.py) against the single agent (week7_agent.py) on 10 Week-6 cases.

    .venv/bin/python week10_race.py select               # pick the 10 Week-6 cases ONCE, before any run -> week10/cases.json
    .venv/bin/python week10_race.py run                  # 10 cases x 3 repeats x 2 arms, then the Week 6 judge -> week10/runs.jsonl
    .venv/bin/python week10_race.py report               # race_table.md, handoffs.log, multiplier.txt from runs.jsonl
    .venv/bin/python week10_race.py failure --case E07   # version worker returns HTTP 500 -> week10/failure_runs.jsonl

Fairness, enforced here rather than promised:
* The cases are Week 6's own (week6/eval_set.jsonl, unchanged). `run` refuses if eval_set.jsonl's sha256
  differs from the one recorded by `select`.
* Same model (week7_tools.MODEL), thinking off for both arms, same tool functions, same output contract,
  Week 8 argument validation on for both.
* Same judge for both arms: the Week 6 judge_v2 prompt, byte-identical, plus the 8 Week 6 assertions.
  A run passes only if no assertion fails AND the judge says PASS (Week 6's "overall" column).
* Jobs from both arms are shuffled together (seeded) and run 3 at a time, so slow API patches hit both.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import week7_agent
import week7_tools
import week10_squad
from week6_eval import call_judge, load_prompt, render_context, run_assertions
from week7_agent import Budgets, run_agent
from week10_squad import run_squad

ROOT = Path(__file__).parent
W10 = ROOT / "week10"
EVAL_SET = ROOT / "week6" / "eval_set.jsonl"
CASES = W10 / "cases.json"
RUNS = W10 / "runs.jsonl"
FAILURE_RUNS = W10 / "failure_runs.jsonl"
JUDGE_VERSION = "v2"
REPEATS = 3
ARMS = ("single", "squad")
CHUNK_ID = re.compile(r"^v[23]-[\w-]+::")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- shared plumbing (both arms)

_search_lock = threading.Lock()
_search = week7_tools.search_docs


def _locked_search(query: str, api_version: str) -> dict:  # chroma + the embedder are not thread-safe
    with _search_lock:
        return _search(query, api_version)


week7_tools.search_docs = week7_tools.TOOL_FUNCS["search_docs"] = _locked_search

# The single agent's tool results are captured per thread, so the judge sees what that run saw.
_seen = threading.local()
_run_tool = week7_agent.run_tool


def _recording_run_tool(name: str, args: dict) -> dict:
    result = _run_tool(name, args)
    getattr(_seen, "items", []).append({"tool": name, "args": args, "result": result})
    return result


week7_agent.run_tool = _recording_run_tool


def configure() -> None:
    week7_tools.THINKING_TOKENS = 0
    week7_tools.VALIDATE_ARGS = True
    week7_tools.warm_up()


def render_answer(output: dict | None) -> str:
    """The Week 7 contract as the Week 6 answer text. One renderer for both arms."""
    if not output:
        return "I don't know based on the provided documents."
    parts = [output["answer"].strip()]
    code = output["v3_code"].strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
    if code:
        parts.append(f"```python\n{code}\n```")
    changes = [d for d in output["deprecations"] if isinstance(d, dict) and d.get("symbol")]
    if changes:
        parts.append("Changed in v3: " + "; ".join(f"`{d['symbol']}` -> `{d.get('replacement', '')}`" for d in changes))
    cite = next((s for s in output["sources"] if isinstance(s, str) and CHUNK_ID.match(s)), None)
    return "\n\n".join(parts) + (f" [chunk:{cite}]" if cite else "")


def documentation_shown(seen: list[dict]) -> list[dict]:
    """Every doc chunk, changelog entry and spec entry the run's tools returned, in the Week 6 context shape."""
    out, ids = [], set()

    def add(chunk_id: str, version: str, text: str) -> None:
        if chunk_id not in ids:
            ids.add(chunk_id)
            out.append({"rank": len(out) + 1, "chunk_id": chunk_id, "sdk_version": version, "text": text})

    for item in seen:
        res = item["result"] if isinstance(item["result"], dict) else {}
        if item["tool"] == "search_docs":
            for r in res.get("results", []):
                add(r["chunk_id"], r["chunk_id"].split("-", 1)[0], r["text"])
        elif item["tool"] == "check_deprecation" and "status" in res:
            add(res.get("source") or f"changelog::{res.get('symbol')}", "v3", json.dumps(res))
        elif item["tool"] == "get_openapi_spec" and "operations" in res:
            add(f"openapi::{res['path']}", "v3", json.dumps(res["operations"]))
    return out


def run_arm(arm: str, case: dict, rep: int, inject_500: bool = False) -> dict:
    if arm == "single":
        _seen.items = []
        log = W10 / "logs" / f"single_{case['id']}_r{rep}.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        r = run_agent(case["question"], Budgets(), log_path=log, echo=False)
        seen, handoffs = _seen.items, []
    else:
        r = run_squad(case["question"], inject_500=inject_500, echo=False)
        seen, handoffs = r["seen"], r["handoffs"]
        log = W10 / "logs" / f"squad_{case['id']}_r{rep}{'_500' if inject_500 else ''}.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("\n".join(json.dumps(e) for e in r["events"]) + "\n")
    answer = render_answer(r["output"])
    row = {"arm": arm, "case": case["id"], "repeat": rep, "status": r["status"], "latency_s": r["latency_s"],
           "tokens": r["tokens"], "cost_usd": round(r["cost_usd"], 6), "llm_calls": r["llm_calls"],
           "answer": answer, "output": r["output"], "context": documentation_shown(seen), "handoffs": handoffs,
           "assertions": run_assertions(case, answer), "log": str(log.relative_to(ROOT))}
    if arm == "squad":
        row.update({k: r.get(k) for k in ("plan", "version_report", "code_report")})
    print(f"{arm:6} {case['id']} r{rep} {r['status']:9} {r['latency_s']:6.1f}s {r['tokens']:6} tok "
          f"${r['cost_usd']:.4f} {r['llm_calls']} calls", flush=True)
    return row


def judge_rows(rows: list[dict], cases: dict[str, dict]) -> None:
    template, _ = load_prompt(JUDGE_VERSION)

    def one(row: dict) -> dict:
        c = cases[row["case"]]
        prompt = (template.replace("{question}", c["question"]).replace("{context}", render_context(row["context"]))
                  .replace("{answer}", row["answer"]))
        return call_judge(prompt)

    with ThreadPoolExecutor(4) as pool:
        for row, verdict in zip(rows, pool.map(one, rows)):
            row["judge"] = {k: verdict[k] for k in ("verdict", "reason", "model")}
            row["assertions_ok"] = all(s != "fail" for s, _ in row["assertions"].values())
            row["pass"] = row["assertions_ok"] and verdict["verdict"] == "PASS"


# ---------------------------------------------------------------- commands

def cmd_select() -> None:
    """Stratified by Week 5 mode (25 -> 10 keeps each mode's share), seeded, decided before any run."""
    if CASES.exists():
        raise SystemExit("week10/cases.json already exists. The case set is fixed; delete it only to restart the race.")
    cases = [json.loads(line) for line in EVAL_SET.read_text().splitlines() if line.strip()]
    by_mode = defaultdict(list)
    for c in cases:
        by_mode[c["mode"]].append(c["id"])
    rng = random.Random(10)
    quota = {m: round(len(ids) * 10 / len(cases)) for m, ids in sorted(by_mode.items())}
    picked = sorted(cid for m, ids in sorted(by_mode.items()) for cid in rng.sample(ids, quota[m]))
    assert len(picked) == 10, quota
    W10.mkdir(exist_ok=True)
    CASES.write_text(json.dumps({
        "rule": "stratified by Week 5 mode: round(n_mode * 10/25) per mode, random.Random(10).sample within mode",
        "quota": quota, "case_ids": picked, "eval_set_sha256": sha(EVAL_SET.read_bytes()), "selected_at_utc": now(),
    }, indent=2))
    print(f"picked {picked} (quota {quota})")


def load_selected() -> dict[str, dict]:
    if not CASES.exists():
        raise SystemExit("run `week10_race.py select` first")
    sel = json.loads(CASES.read_text())
    if sha(EVAL_SET.read_bytes()) != sel["eval_set_sha256"]:
        raise SystemExit("week6/eval_set.jsonl changed since the cases were selected; that moves the ruler.")
    cases = {c["id"]: c for c in map(json.loads, EVAL_SET.read_text().splitlines()) if c["id"] in sel["case_ids"]}
    return dict(sorted(cases.items()))


def cmd_run(workers: int) -> None:
    cases = load_selected()
    configure()
    jobs = [(arm, c, rep) for rep in range(1, REPEATS + 1) for c in cases.values() for arm in ARMS]
    random.Random(10).shuffle(jobs)
    started = now()
    with ThreadPoolExecutor(workers) as pool:
        rows = list(pool.map(lambda j: run_arm(*j), jobs))
    print("judging ...", flush=True)
    judge_rows(rows, cases)
    rows.sort(key=lambda r: (r["arm"], r["case"], r["repeat"]))
    meta = {"meta": True, "started_at_utc": started, "finished_at_utc": now(), "model": week7_tools.MODEL,
            "thinking_tokens": week7_tools.THINKING_TOKENS, "repeats": REPEATS, "judge": f"judge_{JUDGE_VERSION}",
            "case_ids": list(cases)}
    RUNS.write_text("\n".join(json.dumps(r) for r in [meta, *rows]) + "\n")
    cmd_report()


def load_runs(path: Path) -> tuple[dict, list[dict]]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return rows[0], rows[1:]


def nearest_rank(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[max(0, math.ceil(p * len(s)) - 1)]


def summarise(rows: list[dict], repeats: int) -> dict:
    lat = [r["latency_s"] for r in rows]
    return {"runs": len(rows), "pass": sum(r["pass"] for r in rows),
            "assert_pass": sum(r["assertions_ok"] for r in rows),
            "judge_pass": sum(r["judge"]["verdict"] == "PASS" for r in rows),
            "p50": statistics.median(lat), "p99": nearest_rank(lat, 0.99),
            "total_tokens": sum(r["tokens"] for r in rows) / repeats,
            "tokens_per_q": sum(r["tokens"] for r in rows) / len(rows),
            "cost_per_q": sum(r["cost_usd"] for r in rows) / len(rows),
            "calls_per_q": sum(r["llm_calls"] for r in rows) / len(rows)}


def hop_shares(rows: list[dict]) -> list[tuple[str, int, float, int]]:
    total = sum(r["tokens"] for r in rows)
    by_hop, calls = defaultdict(int), defaultdict(int)
    for r in rows:
        for h in r["handoffs"]:
            by_hop[h["hop"]] += h["tokens"]
            calls[h["hop"]] += h["lap"] > 0
    return sorted(((hop, t, t / total, calls[hop]) for hop, t in by_hop.items()), key=lambda x: -x[1])


def cmd_report() -> None:
    meta, rows = load_runs(RUNS)
    cases = load_selected()
    reps = meta["repeats"]
    s = {arm: summarise([r for r in rows if r["arm"] == arm], reps) for arm in ARMS}
    mult = s["squad"]["total_tokens"] / s["single"]["total_tokens"]
    shares = hop_shares([r for r in rows if r["arm"] == "squad"])
    top_hop, top_tok, top_share, top_calls = shares[0]
    multiplier = (f"Context re-send multiplier: squad {s['squad']['total_tokens']:,.0f} / single "
                  f"{s['single']['total_tokens']:,.0f} tokens = {mult:.1f}x. Largest share: "
                  f"\"{top_hop}\" ({top_calls} calls), {top_share:.0%} of all squad tokens.")
    (W10 / "multiplier.txt").write_text(multiplier + "\n")

    lines = [
        "# Week 10 race: docs squad vs single agent", "",
        f"Same {len(cases)} Week-6 cases for both arms (`week6/eval_set.jsonl`, selection in `week10/cases.json`), "
        f"{reps} repeats each, model `{meta['model']}` (thinking off), judge `{meta['judge']}` + 8 Week-6 assertions. "
        "A run passes only if no assertion fails and the judge says PASS.", "",
        "| Arm | Pass rate | p50 latency | p99 latency | Total tokens (10 cases) | Cost / question |",
        "|---|---|---|---|---|---|",
    ]
    for arm, name in (("single", "Single agent (`week7_agent.py`)"), ("squad", "Squad (`week10_squad.py`)")):
        x = s[arm]
        lines.append(f"| {name} | {x['pass']}/{x['runs']} ({x['pass'] / x['runs']:.0%}) | {x['p50']:.1f} s | "
                     f"{x['p99']:.1f} s | {x['total_tokens']:,.0f} | ${x['cost_per_q']:.4f} |")
    lines += [
        "", f"**{multiplier}**", "",
        "Total tokens is one pass over the 10 cases (sum over all runs / repeats). p99 is nearest-rank over "
        f"{s['single']['runs']} runs per arm, so it is the slowest run.", "",
        "## Supporting numbers", "",
        "| Arm | Assertions pass | Judge PASS | Tokens / question | LLM calls / question |", "|---|---|---|---|---|",
    ]
    for arm in ARMS:
        x = s[arm]
        lines.append(f"| {arm} | {x['assert_pass']}/{x['runs']} | {x['judge_pass']}/{x['runs']} | "
                     f"{x['tokens_per_q']:,.0f} | {x['calls_per_q']:.1f} |")
    lines += ["", "## Per case (passes out of repeats)", "", "| Case | Mode | Question | Single | Squad |",
              "|---|---|---|---|---|"]
    for cid, c in cases.items():
        p = {arm: sum(r["pass"] for r in rows if r["arm"] == arm and r["case"] == cid) for arm in ARMS}
        lines.append(f"| {cid} | {c['mode']} | {c['question']} | {p['single']}/{reps} | {p['squad']}/{reps} |")
    lines += ["", "## Why runs failed (first failing check per run)", ""]
    for r in rows:
        if not r["pass"]:
            fails = [f"{n}: {d}" for n, (st, d) in r["assertions"].items() if st == "fail"]
            j = r["judge"]
            why = "; ".join(fails[:2]) or f"judge FAIL: {j['reason']}"
            if fails and j["verdict"] == "FAIL":
                why += " (judge also FAIL)"
            lines.append(f"- {r['arm']} {r['case']} r{r['repeat']}: {why}")
    (W10 / "race_table.md").write_text("\n".join(lines) + "\n")

    log = [f"# handoffs.log: every squad hand-off (one LLM call each) with the tokens it was billed for",
           f"# tokens = input (incl. cache read/creation) + output, from the claude CLI usage block; "
           f"brief_chars = size of the prompt re-sent on that call",
           f"# {'case':4} {'rep':3} {'hand-off':38} {'lap':>3} {'brief_ch':>8} {'in':>6} {'out':>5} {'tokens':>6} {'usd':>8}"]
    for r in rows:
        if r["arm"] != "squad":
            continue
        for h in r["handoffs"]:
            note = f"  ERROR: {h['error']}" if h.get("error") else ""
            log.append(f"  {r['case']:4} r{r['repeat']:<2} {h['hop']:38} {h['lap']:>3} {h['brief_chars']:>8} "
                       f"{h['tokens_in']:>6} {h['tokens_out']:>5} {h['tokens']:>6} {h['cost_usd']:>8.5f}{note}")
        log.append(f"  {r['case']:4} r{r['repeat']:<2} {'= run total':38} {'':>3} {'':>8} {'':>6} {'':>5} "
                   f"{r['tokens']:>6} {r['cost_usd']:>8.5f}")
    total = sum(r["tokens"] for r in rows if r["arm"] == "squad")
    log += ["", f"# totals by hand-off over all {s['squad']['runs']} squad runs ({total:,} tokens)"]
    for hop, tok, share, calls in shares:
        log.append(f"  {hop:38} {calls:>3} calls {tok:>8,} tokens {share:>6.1%}  ({tok / max(calls, 1):,.0f} per call)")
    log += ["", f"# {multiplier}"]
    (W10 / "handoffs.log").write_text("\n".join(log) + "\n")
    print("\n".join(lines[:12]))


def cmd_failure(case_id: str, repeats: int) -> None:
    cases = load_selected()
    configure()
    case = cases[case_id]
    rows = [run_arm("squad", case, rep, inject_500=True) for rep in range(1, repeats + 1)]
    judge_rows(rows, cases)
    meta = {"meta": True, "at_utc": now(), "case": case_id, "injected": "version worker -> HTTP 500", "repeats": repeats}
    FAILURE_RUNS.write_text("\n".join(json.dumps(r) for r in [meta, *rows]) + "\n")
    for r in rows:
        fails = [n for n, (st, _) in r["assertions"].items() if st == "fail"]
        print(f"\n--- {case_id} r{r['repeat']} pass={r['pass']} judge={r['judge']['verdict']} fails={fails}")
        print(r["answer"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["select", "run", "report", "failure"])
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--case", default="E07")
    p.add_argument("--repeats", type=int, default=3)
    a = p.parse_args()
    {"select": cmd_select, "report": cmd_report}.get(a.cmd, lambda: None)()
    if a.cmd == "run":
        cmd_run(a.workers)
    elif a.cmd == "failure":
        cmd_failure(a.case, a.repeats)


if __name__ == "__main__":
    main()
