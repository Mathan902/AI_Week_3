"""Week 12 capstone: the SDK Docs Answer Engine. ONE entry point for everything.

    .venv/bin/python capstone.py ask "how do I paginate through all invoices" --sdk-version 2.4
    .venv/bin/python capstone.py eval                    # 33 cases on the integrated engine -> assertions, trajectory, judge
    .venv/bin/python capstone.py compare                 # before -> after (r0 -> r1 -> r2) from the stored runs
    .venv/bin/python capstone.py loop                    # the closed failure -> test loop, RED then GREEN, live
    .venv/bin/python capstone.py demo                    # the 10-minute demo, parts 1-4 in order
    .venv/bin/python capstone.py serve                   # the MCP server alone, for a client that isn't ours
    .venv/bin/python capstone.py test                    # unit tests (fake LLM, real MCP server), no model cost
    .venv/bin/python capstone.py trace tr-xxxxxxxxxxxx   # one logged trace, span by span

Pieces it wires together (nothing new was learned for this; see week12/architecture.md):
  Week 3-4 structure-aware chunks + MiniLM/Chroma retriever  -> served by week12_server.py (MCP), version-pinned
  Week 5-6 taxonomy + assertions + judge_v2                  -> week12_eval.py on the integrated outputs
  Week 7 plan/act/observe loop with budgets                  -> week12_engine.Engine
  Week 8 trajectory eval (accepted paths as sets)            -> week12_eval.score_trajectory
  Week 9 MCP host (tools discovered from tools/list)         -> week12_engine.Engine.__aenter__
  Week 11 per-request trace, cost/latency per span           -> week12/logs/requests-*.jsonl + mcp_server-*.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PY = sys.executable
W12 = ROOT / "week12"


def sh(*args: str, env: dict | None = None) -> int:
    print(f"\n$ {' '.join(a if ' ' not in a else repr(a) for a in args)}", flush=True)
    return subprocess.call([PY, *args], cwd=ROOT, env={**os.environ, **(env or {})})


def banner(text: str) -> None:
    print("\n" + "=" * 100 + f"\n{text}\n" + "=" * 100, flush=True)


def cmd_ask(a) -> None:
    from week12_engine import ask_once, print_trace
    print_trace(asyncio.run(ask_once(a.question, a.sdk_version, a.release)))


def cmd_eval(a) -> int:
    label = a.label or "r2_latest"
    rc = sh("week12_eval.py", "run", "--release", a.release, "--label", label)
    if not a.no_judge:
        rc |= sh("week12_eval.py", "judge", "--run", label, "--unlabelled-ok")
    return rc


def cmd_compare(a) -> None:
    from week12_eval import (cost_numbers, load_run, looks_like_code_red, pct, rescore_trajectory,
                             trajectory_numbers, wrong_version_rate)
    print(f"{'run':10} {'n':>3} {'outcome (all assertions)':>26} {'wrong-version code':>20} {'parses-but-red':>15} "
          f"{'trace survives MCP':>19} {'traj gap':>9} {'$/question':>11} {'p50 s':>6}")
    for label in a.runs:
        rows = rescore_trajectory(load_run(label))
        w, wn = wrong_version_rate(rows)
        red, parsed = looks_like_code_red(rows)
        prop = [r["trace"]["trace_propagation"]["all_match"] for r in rows if r["trace"]["trace_propagation"]["mcp_calls"]]
        t, c = trajectory_numbers(rows), cost_numbers(rows)
        print(f"{label:10} {len(rows):>3} {pct(sum(r['outcome_pass'] for r in rows), len(rows)):>26} {pct(w, wn):>20} "
              f"{red:>7}/{parsed:<7} {pct(sum(prop), len(prop)):>19} {t['gap_pts']:>+8.1f} {c['mean_cost']:>11.5f} "
              f"{c['p50_ms'] / 1000:>6.1f}")


def cmd_loop(a) -> int:
    banner("CLOSED LOOP: failure found in the integrated system -> test -> RED -> fix -> GREEN, no regressions")
    print("The failure (r0_a C18, trace tr-5871db30a290): Week 11's redaction-on-write rewrote the emitted sample\n"
          "  WEBHOOK_SIGNING_SECRET = os.environ[\"ACME_WEBHOOK_SECRET\"]\n"
          "into\n"
          "  WEBHOOK_SIGNING_SECRET = [REDACTED:secret_assignment]\"ACME_WEBHOOK_SECRET\"]\n"
          "which no longer parses. Neither part has this bug alone; it exists only where the logger meets the agent's output.\n"
          "The tests that now guard it: eval case C33 (week12/eval_cases.jsonl) and\n"
          "tests.test_week12_capstone.Guards.test_redaction_never_corrupts_code_that_references_a_secret")
    banner("1/3  RED: redaction policy v1 (the shipped Week 11 behaviour)")
    red_unit = sh("-W", "ignore", "-m", "unittest", "tests.test_week12_capstone.Guards."
                  "test_redaction_never_corrupts_code_that_references_a_secret", env={"W12_REDACTION_POLICY": "v1"})
    red_case = sh("week12_eval.py", "case", "C33", "--release", "r2", env={"W12_REDACTION_POLICY": "v1"})
    banner("2/3  GREEN: redaction policy v2 (literal secrets only; code references survive)")
    green_unit = sh("-W", "ignore", "-m", "unittest", "tests.test_week12_capstone.Guards."
                    "test_redaction_never_corrupts_code_that_references_a_secret")
    green_case = sh("week12_eval.py", "case", "C33", "--release", "r2")
    banner("3/3  no regressions: the whole unit suite, and the PII cases still redact")
    suite = sh("-W", "ignore", "-m", "unittest", "tests.test_week12_capstone")
    pii = sh("week12_eval.py", "run", "--release", "r2", "--ids", "C31", "C32", "--label", "loop_pii")
    print(f"\nRESULT  v1: unit {'RED' if red_unit else 'green?!'} / C33 {'RED' if red_case else 'green (the model avoided the pattern this time; the unit test is the deterministic guard)'}"
          f"   v2: unit {'GREEN' if not green_unit else 'RED'} / C33 {'GREEN' if not green_case else 'RED'}"
          f"   suite {'GREEN' if not suite else 'RED'}   PII cases {'GREEN' if not pii else 'see output'}")
    return green_unit or green_case or suite


def cmd_demo(a) -> None:
    banner("PART 1 - a real run: a v2.4 caller, version resolved BEFORE retrieval, v2 citation, unasked deprecation")
    sh("capstone.py", "ask", "how do I paginate through all invoices", "--sdk-version", "2.4")
    banner("PART 1b - the removed method, said plainly, for a 3.0 caller")
    sh("capstone.py", "ask", "how do I use client.request() to POST an invoice?", "--sdk-version", "3.0")
    banner("PART 2 - the failures we found (stored traces; week12/taxonomy.md)")
    sh("capstone.py", "trace", "tr-df2fb1813299", "--brief")
    print((W12 / "taxonomy.md").read_text().split("## ")[1][:3500])
    print((W12 / "weaknesses.md").read_text())
    banner("PART 3 - the number that moved (stored runs, n=32/33; week12/eval_report.md)")
    cmd_compare(argparse.Namespace(runs=["r0_a", "r1_a", "r2_a", "r2_b"]))
    sh("week12_eval.py", "summary", "--run", "r2_b")
    banner("PART 4 - what's next: the guard, cost per question, what breaks first at 10x (week12/cost_and_10x.md)")
    print((W12 / "cost_and_10x.md").read_text().split("\n## ")[0])
    print("\nRun `capstone.py loop` for the closed failure -> test loop, live.")


def cmd_trace(a) -> None:
    for f in sorted((W12 / "logs").glob("requests-*.jsonl")):
        for line in f.read_text().splitlines():
            t = json.loads(line)
            if t["trace_id"] == a.trace_id:
                if a.brief:
                    from week12_engine import print_trace
                    print(f"question: {t['question']}   (IDE flag: {t['sdk_version_flag']})")
                    print_trace(t)
                else:
                    print(json.dumps(t, indent=1))
                server = [json.loads(l) for s in (W12 / "logs").glob("mcp_server-*.jsonl")
                          for l in s.read_text().splitlines() if a.trace_id in l]
                print(f"\nserver-side spans under {a.trace_id}: {len(server)}")
                for s in server:
                    print(f"   {s['span']:32} {s['latency_ms']:>7} ms  args={s['args']}")
                return
    sys.exit(f"{a.trace_id} not found in week12/logs")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ask")
    s.add_argument("question")
    s.add_argument("--sdk-version", help="the caller's installed SDK version (the IDE plugin sends it), e.g. 2.4")
    s.add_argument("--release", default="r2", choices=["r0", "r1", "r2"])
    s = sub.add_parser("eval")
    s.add_argument("--release", default="r2", choices=["r0", "r1", "r2"])
    s.add_argument("--label")
    s.add_argument("--no-judge", action="store_true")
    s = sub.add_parser("compare")
    s.add_argument("--runs", nargs="+", default=["r0_a", "r1_a", "r2_a", "r2_b"])
    sub.add_parser("loop")
    sub.add_parser("demo")
    sub.add_parser("serve")
    sub.add_parser("test")
    s = sub.add_parser("trace")
    s.add_argument("trace_id")
    s.add_argument("--brief", action="store_true")
    a = p.parse_args()
    if a.cmd == "ask":
        cmd_ask(a)
    elif a.cmd == "eval":
        sys.exit(cmd_eval(a))
    elif a.cmd == "compare":
        cmd_compare(a)
    elif a.cmd == "loop":
        sys.exit(cmd_loop(a))
    elif a.cmd == "demo":
        cmd_demo(a)
    elif a.cmd == "serve":
        os.execv(PY, [PY, str(ROOT / "week12_server.py")])
    elif a.cmd == "test":
        sys.exit(sh("-W", "ignore", "-m", "unittest", "tests.test_week12_capstone", "-v"))
    elif a.cmd == "trace":
        cmd_trace(a)


if __name__ == "__main__":
    main()
