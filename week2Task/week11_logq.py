"""Week 11: slice the request logs. The support drill is done with this and nothing else.

    .venv/bin/python week11_logq.py stats                                     # what is in the logs
    .venv/bin/python week11_logq.py find --since 2026-10-12 --until 2026-10-19 --input-type code_paste
    .venv/bin/python week11_logq.py find --user u-6f69 --prompt v1
    .venv/bin/python week11_logq.py find --q-re 'paginat'                      # regex over the question (input)
    .venv/bin/python week11_logq.py find --out-re 'paginate_auto'              # regex over answer_text (output)
    .venv/bin/python week11_logq.py find --code-re 'paginate_auto'             # regex over the generated code only
    .venv/bin/python week11_logq.py find --cost-outlier                        # cost above p99
    .venv/bin/python week11_logq.py reindex                                   # bonus: output index (backfill)
    .venv/bin/python week11_logq.py find --flag deprecated_call_in_code       # bonus: one-field find
    .venv/bin/python week11_logq.py show tr-xxxxxxxxxxxx                        # the full trace
    .venv/bin/python week11_logq.py stages --trace tr-xxxxxxxxxxxx              # cost/latency by stage + volume

Slices combine with AND. `find` prints one row per trace: ts, trace_id, user, input_type, prompt version, cost,
the first retrieved context id and the question.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
LOG_DIR = ROOT / "week11" / "logs"
INDEX = LOG_DIR / "output_index.jsonl"  # backfill for schema-1 traces, written by `reindex`
DEPRECATIONS = json.loads((ROOT / "week6" / "deprecations.json").read_text())


def output_index(trace: dict, chunk_text: dict[str, str]) -> dict:
    """Bonus (schema 2): index the OUTPUT, not just the input. Written at log time from then on.

    deprecated_in_code  deprecated symbols matched in the generated code block (week6/deprecations.json)
    served_from         per symbol: "retrieved_v2_page" if a retrieved v2 chunk contains it (retrieval served the
                        archived page), else "not_in_retrieved_v2" (the model wrote it from memory, or the trace
                        was altered after the fact)
    flags               deprecated_call_in_code (v3 target only) and code_contradicts_context
    """
    code = (trace.get("output") or {}).get("code", "") or ""
    found = [d for d in DEPRECATIONS if re.search(d["pattern"], code)]
    v2_text = "\n".join(chunk_text.get(c, "") for c in trace["retrieved_context_ids"] if c.startswith("v2-"))
    served = {d["symbol"]: "retrieved_v2_page" if re.search(d["pattern"], v2_text) else "not_in_retrieved_v2"
              for d in found}
    flags = []
    if found and trace.get("sdk_target") == "v3":
        flags.append("deprecated_call_in_code")
        if "not_in_retrieved_v2" in served.values():
            flags.append("code_contradicts_context")
    return {"deprecated_in_code": [d["symbol"] for d in found], "served_from": served, "flags": flags}


def chunk_texts() -> dict[str, str]:
    from chunking import load_pages, make_chunks
    return {c.chunk_uid: c.text for c in make_chunks(load_pages(ROOT / "corpus"), "structured")}


def load(log_dir: Path = LOG_DIR) -> list[dict]:
    rows = []
    for f in sorted(log_dir.glob("requests-*.jsonl")):
        rows += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    index = log_dir / INDEX.name
    if index.exists():
        backfill = {r["trace_id"]: r["output_index"] for r in map(json.loads, index.read_text().splitlines())}
        for t in rows:
            if "output_index" not in t and t["trace_id"] in backfill:
                t["output_index"] = backfill[t["trace_id"]]
    return rows


def reindex(log_dir: Path = LOG_DIR) -> int:
    """Recompute the output index for every trace (the ingest job; run it whenever logs land)."""
    texts = chunk_texts()
    rows = [{"trace_id": t["trace_id"], "output_index": output_index(t, texts)} for t in load(log_dir)]
    (log_dir / INDEX.name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    return len(rows)


def code_of(t: dict) -> str:
    return (t.get("output") or {}).get("code", "") or ""


def p99(values: list[float]) -> float:
    return statistics.quantiles(values, n=100)[98] if len(values) > 1 else (values[0] if values else 0.0)


def find(rows: list[dict], a: argparse.Namespace) -> list[dict]:
    out = rows
    if a.since:
        out = [t for t in out if t["ts"] >= a.since]
    if a.until:
        out = [t for t in out if t["ts"] < a.until]
    if a.user:
        out = [t for t in out if t["user_id"] == a.user]
    if a.prompt:
        out = [t for t in out if t["prompt_version"] == a.prompt]
    if a.input_type:
        out = [t for t in out if t["input_type"] == a.input_type]
    if a.target:
        out = [t for t in out if t.get("sdk_target") == a.target]
    if a.q_re:
        out = [t for t in out if re.search(a.q_re, t["question"], re.I)]
    if a.out_re:
        out = [t for t in out if re.search(a.out_re, t["answer_text"], re.I)]
    if a.code_re:
        out = [t for t in out if re.search(a.code_re, code_of(t))]
    if a.ctx_re:
        out = [t for t in out if any(re.search(a.ctx_re, c) for c in t["retrieved_context_ids"])]
    if a.cost_outlier:
        cut = p99([t["cost_usd"] for t in rows])
        out = [t for t in out if t["cost_usd"] > cut]
    if a.flag:  # schema >= 2 only: the output index written at log time
        out = [t for t in out if a.flag in (t.get("output_index") or {}).get("flags", [])]
    return out


def row(t: dict) -> str:
    ctx = t["retrieved_context_ids"][0] if t["retrieved_context_ids"] else "-"
    return (f"{t['ts']}  {t['trace_id']}  {t['user_id']:7} {t['input_type']:13} {t['prompt_version']:3} "
            f"${t['cost_usd']:.5f}  {ctx[:38]:38}  {t['question'][:60]}")


def stages(rows: list[dict], trace_id: str | None) -> None:
    """Cost, tokens and latency per stage: for one trace, and the mean / p50 / p99 over all traffic."""
    from datetime import datetime

    names = ("retrieval", "tools", "generation")
    if trace_id:
        t = next(t for t in rows if t["trace_id"] == trace_id)
        print(f"trace {trace_id}: total ${t['cost_usd']:.7f}, {t['latency_ms']} ms")
        for s in t["spans"]:
            share = s["cost_usd"] / t["cost_usd"] if t["cost_usd"] else 0
            print(f"  {s['name']:10} ${s['cost_usd']:.7f} ({share:6.1%})  {s['latency_ms']:>8} ms  {s['tokens']}")
    traffic = [t for t in rows if t.get("ts_source") == "traffic-replay"] or rows
    print(f"\nall traffic: {len(traffic)} traces")
    total = sum(t["cost_usd"] for t in traffic)
    for n in names:
        spans = [s for t in traffic for s in t["spans"] if s["name"] == n]
        cost = [s["cost_usd"] for s in spans]
        lat = sorted(s["latency_ms"] for s in spans)
        tok = [sum(s["tokens"].values()) for s in spans]
        print(f"  {n:10} mean ${statistics.mean(cost):.7f}/query ({sum(cost) / total if total else 0:6.1%})  "
              f"latency p50 {statistics.median(lat):.1f} ms p99 {p99(lat):.1f} ms  tokens mean {statistics.mean(tok):.0f}")
    lat = [t["latency_ms"] for t in traffic]
    print(f"  {'total':10} mean ${total / len(traffic):.7f}/query  latency p50 {statistics.median(lat):.0f} ms "
          f"p99 {p99(lat):.0f} ms")
    gen = [s for t in traffic for s in t["spans"] if s["name"] == "generation"]
    print(f"  generation tokens/query: in {statistics.mean(s['tokens']['in'] for s in gen):.0f}, "
          f"out {statistics.mean(s['tokens']['out'] for s in gen):.0f}")
    by_day = Counter(t["ts"][:10] for t in traffic)
    by_hour = Counter(t["ts"][:13] for t in traffic)
    by_min = Counter(t["ts"][:16] for t in traffic)
    days = (datetime.fromisoformat(max(t["ts"] for t in traffic)) -
            datetime.fromisoformat(min(t["ts"] for t in traffic))).total_seconds() / 86400
    print(f"\nvolume: {len(traffic)} queries over {days:.1f} days = {len(traffic) / days:.1f}/day; "
          f"busiest day {max(by_day.values())} ({max(by_day, key=by_day.get)}); busiest hour "
          f"{max(by_hour.values())} ({max(by_hour, key=by_hour.get)}:00); busiest minute {max(by_min.values())}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    f = sub.add_parser("find")
    for opt in ("since", "until", "user", "prompt", "input-type", "target", "q-re", "out-re", "code-re",
                "ctx-re", "flag"):
        f.add_argument(f"--{opt}")
    f.add_argument("--cost-outlier", action="store_true")
    f.add_argument("--limit", type=int, default=40)
    s = sub.add_parser("show")
    s.add_argument("trace_id")
    sub.add_parser("reindex")
    st = sub.add_parser("stages")
    st.add_argument("--trace")
    a = p.parse_args()
    rows = load()

    if a.cmd == "stages":
        return stages(rows, a.trace)
    if a.cmd == "reindex":
        print(f"indexed {reindex()} traces -> {INDEX.relative_to(ROOT)}")
        return

    if a.cmd == "stats":
        print(f"{len(rows)} traces, {rows[0]['ts'] if rows else '-'} .. {max(t['ts'] for t in rows) if rows else '-'}")
        for key in ("prompt_version", "input_type", "sdk_target", "status", "schema"):
            print(f"  {key:15} {dict(Counter(t.get(key) for t in rows))}")
        print(f"  users          {len({t['user_id'] for t in rows})}")
        print(f"  fields         {sorted(rows[-1])}")
    elif a.cmd == "find":
        hits = find(rows, a)
        print(f"{len(hits)} of {len(rows)} traces")
        for t in hits[:a.limit]:
            print(row(t))
    else:
        t = next((t for t in rows if t["trace_id"] == a.trace_id), None)
        print(json.dumps(t, indent=2) if t else f"no trace {a.trace_id}")


if __name__ == "__main__":
    main()
