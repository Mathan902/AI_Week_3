"""Week 11: the Week 6 suite run against the production app, plus the cases production failures added.

    .venv/bin/python week11_suite.py run --prompt v1 --label red      # before the fix
    .venv/bin/python week11_suite.py run --prompt v2 --label green    # after the fix
    .venv/bin/python week11_suite.py diff red green                   # every case that changed, regressions first
    .venv/bin/python week11_suite.py summary --before red_r1 red_r2 red_r3 --after green_r1 green_r2 green_r3

Cases: the 25 Week 6 cases (week6/eval_set.jsonl, unchanged) + every case in week11/eval_cases.jsonl.
Gate per case, the same as Week 10: no assertion fails AND judge_v2 says PASS. The assertions are the 8 Week 6
ones plus `no_deprecated_call_in_code`, which applies only to cases that carry `code_must_not` (a regex list the
generated code block must not match). The Week 6 deprecation assertion passes any answer that says "removed"
somewhere, even when the code block still calls the removed method, so it cannot catch this incident.

Output: week11/suite_<label>.txt (what the terminal shows) and week11/suite_<label>.jsonl (every row).
"""
from __future__ import annotations

import argparse
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from chunking import load_pages, make_chunks
from week6_eval import FENCE, call_judge, load_prompt, render_context, run_assertions, split_answer
from week11_app import RELEASES, DocsAssistant

ROOT = Path(__file__).parent
W11 = ROOT / "week11"
CASE_FILES = [ROOT / "week6" / "eval_set.jsonl", W11 / "eval_cases.jsonl"]


def load_cases() -> list[dict]:
    cases = []
    for f in CASE_FILES:
        if f.exists():
            cases += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    return cases


def check_no_deprecated_call(answer: str, case: dict) -> tuple[str, str]:
    banned = case.get("code_must_not") or []
    if not banned:
        return "n/a", "no code_must_not on this case"
    code = "\n".join(FENCE.findall(split_answer(answer)[0]))
    hit = [p for p in banned if re.search(p, code)]
    return ("fail", f"code block matches /{hit[0]}/") if hit else ("pass", f"code clear of {len(banned)} pattern(s)")


def context_shown(trace: dict, texts: dict[str, str]) -> list[dict]:
    out = [{"rank": r["rank"], "chunk_id": r["chunk_id"], "sdk_version": r["sdk_version"],
            "text": texts.get(r["chunk_id"], "")} for r in trace["retrieved"]]
    for c in trace["tool_calls"]:
        cid = (f"openapi::{c['args']['path']}" if c["tool"] == "get_openapi_spec"
               else c["result"].get("source") or f"changelog::{c['args']['symbol']}")
        out.append({"rank": len(out) + 1, "chunk_id": cid,
                    "sdk_version": "v3", "text": json.dumps(c["result"])})
    return out


def run(prompt_version: str, label: str, workers: int) -> None:
    cases = load_cases()
    bot = DocsAssistant(log_dir=None)
    texts = {c.chunk_uid: c.text for c in make_chunks(load_pages(ROOT / "corpus"), "structured")}
    template, _ = load_prompt("v2")
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def one(case: dict) -> dict:
        t = bot.ask(case["question"], user_id="eval", session_id=f"suite-{label}", prompt_version=prompt_version)
        answer = t["answer_text"]
        asserts = run_assertions(case, answer)
        asserts["no_deprecated_call_in_code"] = check_no_deprecated_call(answer, case)
        if case.get("spec") == "v2":  # endpoints_in_spec knows only the v3 OpenAPI file
            asserts["endpoints_in_spec"] = ("n/a", "v2 legacy case; no v2 spec in the repo")
        verdict = call_judge(template.replace("{question}", case["question"])
                             .replace("{context}", render_context(context_shown(t, texts)))
                             .replace("{answer}", answer))
        ok = all(s != "fail" for s, _ in asserts.values())
        return {"case": case["id"], "question": case["question"], "source": case["source"], "answer": answer,
                "retrieved_context_ids": t["retrieved_context_ids"], "assertions": asserts, "assertions_ok": ok,
                "judge": {k: verdict[k] for k in ("verdict", "reason")}, "pass": ok and verdict["verdict"] == "PASS",
                "cost_usd": t["cost_usd"], "latency_ms": t["latency_ms"], "trace_id": t["trace_id"]}

    with ThreadPoolExecutor(workers) as pool:
        rows = list(pool.map(one, cases))
    meta = {"meta": True, "label": label, "prompt_version": prompt_version, "release": RELEASES[prompt_version],
            "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cases": len(rows), "judge": "judge_v2"}
    (W11 / f"suite_{label}.jsonl").write_text("\n".join(json.dumps(r) for r in [meta, *rows]) + "\n")
    buf = io.StringIO()
    with redirect_stdout(buf):
        report(meta, rows)
    (W11 / f"suite_{label}.txt").write_text(buf.getvalue())
    print(buf.getvalue())


def report(meta: dict, rows: list[dict]) -> None:
    n = len(rows)
    print(f"$ .venv/bin/python week11_suite.py run --prompt {meta['prompt_version']} --label {meta['label']}")
    print(f"Week 11 suite, release {meta['prompt_version']} {json.dumps(meta['release'])}")
    print(f"{n} cases ({sum(not r['case'].startswith('W11') for r in rows)} Week 6 + "
          f"{sum(r['case'].startswith('W11') for r in rows)} from week11/eval_cases.jsonl), {meta['started_at_utc']}\n")
    for r in rows:
        fails = [f"{k}: {d}" for k, (s, d) in r["assertions"].items() if s == "fail"]
        why = "; ".join(fails) or ("" if r["judge"]["verdict"] == "PASS" else f"judge: {r['judge']['reason'][:90]}")
        print(f"  {'PASS' if r['pass'] else 'FAIL'}  {r['case']:6} {r['question'][:46]:46} {why}")
    print(f"\nassertions {sum(r['assertions_ok'] for r in rows)}/{n}   "
          f"judge {sum(r['judge']['verdict'] == 'PASS' for r in rows)}/{n}")
    status = "GREEN" if all(r["pass"] for r in rows if r["case"].startswith("W11")) else "RED"
    print(f"SUITE {meta['label']}: {sum(r['pass'] for r in rows)}/{n} pass  "
          f"(incident cases: {status})")


def diff(a: str, b: str) -> None:
    load = lambda l: {r["case"]: r for r in map(json.loads, (W11 / f"suite_{l}.jsonl").read_text().splitlines()[1:])}
    ra, rb = load(a), load(b)
    print(f"{a}: {sum(r['pass'] for r in ra.values())}/{len(ra)}   {b}: {sum(r['pass'] for r in rb.values())}/{len(rb)}")
    for cid in sorted(set(ra) | set(rb), key=lambda c: (not (c in ra and ra[c]["pass"] and not rb[c]["pass"]), c)):
        pa, pb = ra.get(cid, {}).get("pass"), rb.get(cid, {}).get("pass")
        if pa != pb:
            tag = "REGRESSION" if pa and not pb else ("fixed" if pb else "new case, fails")
            print(f"  {tag:15} {cid}")


def summary(before: list[str], after: list[str]) -> None:
    """Per-case passes over repeated runs, so one LLM coin-flip is not read as a fix or a regression."""
    load = lambda l: {r["case"]: r for r in map(json.loads, (W11 / f"suite_{l}.jsonl").read_text().splitlines()[1:])}
    ra, rb = [load(l) for l in before], [load(l) for l in after]
    rel = lambda l: json.loads((W11 / f"suite_{l[0]}.jsonl").read_text().splitlines()[0])["prompt_version"]
    print(f"| Case | Question | before ({rel(before)}) | after ({rel(after)}) | |\n|---|---|---|---|---|")
    for cid in ra[0]:
        a, b = sum(r[cid]["pass"] for r in ra), sum(r[cid]["pass"] for r in rb)
        tag = "fixed" if b > a else ("**REGRESSION**" if b < a else "")
        print(f"| {cid} | {ra[0][cid]['question'][:48]} | {a}/{len(ra)} | {b}/{len(rb)} | {tag} |")
    print(f"| **suite** | | {' · '.join(str(sum(r['pass'] for r in x.values())) + '/' + str(len(x)) for x in ra)} | "
          f"{' · '.join(str(sum(r['pass'] for r in x.values())) + '/' + str(len(x)) for x in rb)} | |")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--prompt", required=True, choices=sorted(RELEASES))
    r.add_argument("--label", required=True)
    r.add_argument("--workers", type=int, default=4)
    d = sub.add_parser("diff")
    d.add_argument("a")
    d.add_argument("b")
    sm = sub.add_parser("summary")
    sm.add_argument("--before", nargs="+", required=True)
    sm.add_argument("--after", nargs="+", required=True)
    a = p.parse_args()
    if a.cmd == "run":
        run(a.prompt, a.label, a.workers)
    elif a.cmd == "summary":
        summary(a.before, a.after)
    else:
        diff(a.a, a.b)


if __name__ == "__main__":
    main()
