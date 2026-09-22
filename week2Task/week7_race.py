"""Week 7: race the agent against the fixed workflow on the same 10 questions.

    .venv/bin/python week7_race.py               # 10 questions x 3 repeats x 2 systems -> week7/race.csv
    .venv/bin/python week7_race.py --no-thinking  # extended thinking off for BOTH systems -> race_no_thinking.csv

Jobs from both systems are shuffled together (seeded) and run 4 at a time, so a slow patch of API
latency hits both systems alike. The vector index is loaded before the clock starts.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import week7_tools
from week7_agent import Budgets, run_agent
from week7_tools import W7, grade
from week7_workflow import run_workflow

LOG_DIR = W7 / "logs" / "race"
_search_lock = threading.Lock()
_search = week7_tools.search_docs


def _locked_search(query: str, api_version: str) -> dict:  # chroma + the embedder are not thread-safe
    with _search_lock:
        return _search(query, api_version)


week7_tools.search_docs = week7_tools.TOOL_FUNCS["search_docs"] = _locked_search
import week7_workflow  # noqa: E402  (re-bind the workflow's imported name too)
week7_workflow.search_docs = _locked_search


def run_one(job: tuple[str, dict, int]) -> dict:
    system, q, rep = job
    if system == "agent":
        log = LOG_DIR / f"agent_{q['id']}_r{rep}.jsonl"
        r = run_agent(q["question"], Budgets(), log_path=log, echo=False)
    else:
        r = run_workflow(q["question"], echo=False)
    ok, fails = grade(q, r["output"])
    row = {"system": system, "qid": q["id"], "class": q["class"], "repeat": rep, "pass": int(ok),
           "status": r["status"], "latency_s": r["latency_s"], "tokens": r["tokens"],
           "cost_usd": round(r["cost_usd"], 6), "llm_calls": r["llm_calls"], "fails": "; ".join(fails),
           "v3_code": (r["output"] or {}).get("v3_code", "")}
    print(f"{system:8} {q['id']} r{rep} {'PASS' if ok else 'FAIL'} {r['latency_s']:6.1f}s {r['tokens']:6} tok "
          f"${r['cost_usd']:.4f} {r['llm_calls']} calls {'; '.join(fails)[:80]}", flush=True)
    return row


def summarise(rows: list[dict], repeats: int) -> list[dict]:
    out = []
    for system in ("agent", "workflow"):
        for cls in ("all", "dependent", "lookup"):
            rs = [r for r in rows if r["system"] == system and (cls == "all" or r["class"] == cls)]
            n_q = len({r["qid"] for r in rs})
            out.append({
                "system": system, "questions": cls, "runs": len(rs),
                "pass_rate": round(sum(r["pass"] for r in rs) / len(rs), 3),
                "p50_latency_s": round(statistics.median(r["latency_s"] for r in rs), 2),
                "total_tokens": round(sum(r["tokens"] for r in rs) / repeats),       # per pass over these questions
                "tokens_per_question": round(sum(r["tokens"] for r in rs) / len(rs)),
                "cost_per_question_usd": round(sum(r["cost_usd"] for r in rs) / len(rs), 5),
                "llm_calls_per_question": round(sum(r["llm_calls"] for r in rs) / len(rs), 2),
                "n_questions": n_q,
            })
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--no-thinking", action="store_true", help="MAX_THINKING_TOKENS=0 for both systems")
    a = p.parse_args()
    tag = "_no_thinking" if a.no_thinking else ""
    if a.no_thinking:
        week7_tools.THINKING_TOKENS = 0
    questions = [json.loads(line) for line in (W7 / "questions.jsonl").read_text().splitlines()]
    global LOG_DIR
    LOG_DIR = W7 / "logs" / f"race{tag}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    week7_tools.warm_up()
    jobs = [(s, q, rep) for rep in range(1, a.repeats + 1) for q in questions for s in ("agent", "workflow")]
    random.Random(7).shuffle(jobs)
    with ThreadPoolExecutor(a.workers) as pool:
        rows = list(pool.map(run_one, jobs))
    rows.sort(key=lambda r: (r["system"], r["qid"], r["repeat"]))
    with (W7 / f"race_runs{tag}.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = summarise(rows, a.repeats)
    with (W7 / f"race{tag}.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    print(f"\n{len(questions)} questions x {a.repeats} repeats, model {week7_tools.MODEL}, "
          f"thinking {'OFF' if a.no_thinking else 'default'}, same tools and contract")
    print(f"{'system':9} {'questions':10} {'pass rate':>9} {'p50 s':>7} {'total tok':>10} {'tok/q':>7} {'$/q':>8} {'calls/q':>7}")
    for s in summary:
        print(f"{s['system']:9} {s['questions']:10} {s['pass_rate']:>9.0%} {s['p50_latency_s']:>7.1f} "
              f"{s['total_tokens']:>10} {s['tokens_per_question']:>7} {s['cost_per_question_usd']:>8.4f} "
              f"{s['llm_calls_per_question']:>7.2f}")
    per_q = defaultdict(dict)
    for r in rows:
        per_q[r["qid"]].setdefault(r["system"], []).append(r["pass"])
    print("\nper question (passes out of repeats):  " + "  ".join(
        f"{qid} a{sum(v.get('agent', []))}/w{sum(v.get('workflow', []))}" for qid, v in sorted(per_q.items())))


if __name__ == "__main__":
    main()
