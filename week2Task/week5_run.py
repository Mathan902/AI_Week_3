"""Week 5: generate traces, draw the seeded sample, replay one trace.

    .venv/bin/python week5_run.py traffic          # every question in week5/traffic_questions.txt -> traces.jsonl
    .venv/bin/python week5_run.py sample --seed N  # 20 random trace_ids -> week5/sample.md (reading view)
    .venv/bin/python week5_run.py replay --seed N  # one random trace_id, replayed from the trace alone
    .venv/bin/python week5_run.py demo --seed N    # bonus: 10 of the golden_set (DX demo) questions, traced
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from tracing import TRACE_FILE, TracedAssistant, load_traces, replay_full, replay_generation

ROOT = Path(__file__).parent
OUT = ROOT / "week5"
DEMO_TRACE_FILE = OUT / "demo_traces.jsonl"


def read_questions(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def reading_view(trace: dict, number: int) -> str:
    lines = [f"## {number:02d}. `{trace['trace_id']}` — {trace['question']}", "",
             "| rank | chunk_id | ver | dense | final |", "|---|---|---|---|---|"]
    for r in trace["retrieved"]:
        lines.append(f"| {r['rank']} | `{r['chunk_id']}` | {r['sdk_version']} | {r['dense']:.3f} | {r['final']:.3f} |")
    lines += ["", "<details><summary>retrieved text</summary>", ""]
    for r in trace["retrieved"]:
        lines += [f"**#{r['rank']} `{r['chunk_id']}`**", "", "```", r["text"], "```", ""]
    lines += ["</details>", "", f"**Output:** `{trace['raw_output']}`", ""]
    return "\n".join(lines)


def seeded_pick(ids: list[str], seed: int, n: int) -> list[str]:
    return random.Random(seed).sample(sorted(ids), n)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["traffic", "sample", "replay", "demo"])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    if args.cmd == "traffic":
        bot = TracedAssistant()
        for i, question in enumerate(read_questions(OUT / "traffic_questions.txt")):
            bot.ask(question, session=f"s{i // 5:03d}")
        print(f"{len(load_traces())} traces in {TRACE_FILE}")

    elif args.cmd == "sample":
        traces = {t["trace_id"]: t for t in load_traces()}
        picked = seeded_pick(list(traces), args.seed, args.n)
        header = (f"# Seeded random sample\n\n`random.Random({args.seed}).sample(sorted(trace_ids), {args.n})` "
                  f"over {len(traces)} traces in `week5/traces.jsonl`.\n\n")
        body = "\n".join(reading_view(traces[tid], i) for i, tid in enumerate(picked, start=1))
        (OUT / "sample.md").write_text(header + body, encoding="utf-8")
        print(json.dumps(picked))

    elif args.cmd == "replay":
        traces = {t["trace_id"]: t for t in load_traces()}
        tid = seeded_pick(list(traces), args.seed, 1)[0]
        trace = traces[tid]
        gen_only = replay_generation(trace)
        bot = TracedAssistant(trace_file=OUT / "replay_scratch.jsonl")
        hits, full = replay_full(trace, bot.store)
        replay = {
            "seed": args.seed,
            "trace_id": tid,
            "question": trace["question"],
            "original_output": trace["raw_output"],
            "replayed_output_generation_only": gen_only,
            "replayed_output_full_pipeline": full,
            "original_retrieved": [(r["chunk_id"], r["dense"], r["final"]) for r in trace["retrieved"]],
            "replayed_retrieved": [(h.chunk.chunk_uid, round(h.dense_score, 6), round(h.final_score, 6)) for h in hits],
            "versions_now_vs_trace": {
                k: {"trace": trace[k], "now": bot.static[k]}
                for k in ("generator_version", "retriever_version", "corpus_version", "model")
            },
            "output_identical": gen_only == full == trace["raw_output"],
        }
        (OUT / "replay_evidence.json").write_text(json.dumps(replay, indent=2), encoding="utf-8")
        (OUT / "replay_scratch.jsonl").unlink(missing_ok=True)
        print(json.dumps(replay, indent=2))

    elif args.cmd == "demo":
        golden = [json.loads(l) for l in (ROOT / "golden_set.jsonl").read_text().splitlines() if l.strip()]
        picked = seeded_pick([q["id"] for q in golden], args.seed, 10)
        DEMO_TRACE_FILE.unlink(missing_ok=True)
        bot = TracedAssistant(trace_file=DEMO_TRACE_FILE)
        by_id = {q["id"]: q for q in golden}
        traces = [bot.ask(by_id[qid]["question"], session=f"demo-{qid}") for qid in picked]
        body = "\n".join(reading_view(t, i) for i, t in enumerate(traces, start=1))
        (OUT / "demo_sample.md").write_text(
            f"# Demo-set sample (bonus)\n\n`random.Random({args.seed}).sample(sorted(golden ids), 10)` = {picked}\n\n" + body,
            encoding="utf-8")
        print(json.dumps(picked))


if __name__ == "__main__":
    main()
