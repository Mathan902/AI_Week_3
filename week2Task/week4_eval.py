from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from chunking import load_pages, make_chunks
from generate import REFUSAL, answer, lexical_support
from hybrid import HybridRetriever
from run_eval import common_terms
from vector_store import Hit, SdkVectorStore

ROOT = Path(__file__).parent
OUT = ROOT / "week4_output"
GOLDEN = ROOT / "golden_set.jsonl"
COLLECTION = "sdk_structured"
K = 3
DIAG_DEPTH = 25  # how deep the inspection view looks for a missed gold chunk
LATENCY_REPEATS = 7


class BaselineRetriever:
    """The Week 3 retriever, unchanged: dense MiniLM + lexical-overlap boost."""

    name = "baseline"

    def __init__(self, store: SdkVectorStore, collection: str):
        self.store = store
        self.collection = collection

    def retrieve(self, query: str, k: int) -> list[Hit]:
        return self.store.search(self.collection, query, top_k=k)


RETRIEVERS = {"baseline": BaselineRetriever, "hybrid": HybridRetriever}


def load_golden() -> list[dict]:
    return [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]


def correct_ids(q: dict) -> set[str]:
    """Lenient: the tagged chunk or any chunk that also states the answer."""
    return {q["chunk_id"], *q["also_correct"]}


def first_correct_rank(hits: list[Hit], q: dict, strict: bool = True) -> int:
    """Strict (the scored metric) counts only the one tagged chunk_id."""
    ids = {q["chunk_id"]} if strict else correct_ids(q)
    for rank, hit in enumerate(hits, start=1):
        if hit.chunk.chunk_uid in ids:
            return rank
    return 0


def answer_is_correct(reply: str, q: dict) -> bool:
    return reply != REFUSAL and all(f.lower() in reply.lower() for f in q["answer_facts"])


def refusal_reason(q: dict, hits: list[Hit], common: set[str]) -> str:
    if not hits or hits[0].final_score < 0.40:
        return f"score gate (top-1 final={hits[0].final_score:.3f} < 0.40)" if hits else "no hits"
    support = lexical_support(q["question"], hits, common_terms=common)
    if support < 0.6:
        return f"lexical-support gate refused (support={support:.2f} < 0.60)"
    return "generator quoted a different chunk"


def label(q: dict, hits: list[Hit], deep: list[Hit], reply: str, corpus_ids: set[str],
          common: set[str]) -> tuple[str, str]:
    """PASS / R / G / NIC, with one line of evidence read off the inspection view."""
    top = ", ".join(f"{h.chunk.chunk_uid}" for h in hits)
    if not correct_ids(q) & corpus_ids:
        return "NIC", f"none of {sorted(correct_ids(q))} exists in the indexed corpus"
    rank = first_correct_rank(hits, q)
    if rank == 0:
        deep_rank = first_correct_rank(deep, q)
        where = f"sits at rank {deep_rank} of {DIAG_DEPTH}" if deep_rank else f"not even in top-{DIAG_DEPTH}"
        token = q["exact_token"]
        token_note = ""
        if token:
            holders = sum(1 for h in hits if token.lower() in h.chunk.text.lower())
            token_note = f"; {holders}/{len(hits)} of the top-3 contain `{token}`"
        return "R", f"gold `{q['chunk_id']}` {where}{token_note}; top-3 = [{top}]"
    if not answer_is_correct(reply, q):
        why = refusal_reason(q, hits, common) if reply == REFUSAL else f"quoted {reply[-60:]!r}"
        return "G", (
            f"gold `{q['chunk_id']}` at rank {rank} of top-3 containing {q['answer_facts']}, "
            f"but answer lacks it — {why}"
        )
    return "PASS", f"correct chunk at rank {rank}; answer contains {q['answer_facts']}"


def inspection_block(q: dict, hits: list[Hit], reply: str, verdict: str, evidence: str,
                     explain: dict | None = None) -> str:
    ids = correct_ids(q)
    lines = [
        f"## {q['id']} — {q['question']}",
        f"- Gold: `{q['chunk_id']}`" + (f" (also correct: {', '.join(f'`{c}`' for c in q['also_correct'])})" if q["also_correct"] else ""),
        f"- Exact token: `{q['exact_token']}` ({q['token_kind']})" if q["exact_token"] else "- Exact token: none",
        "",
        "| rank | chunk_id | ver | dense | final | fusion | gold? | text |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for rank, hit in enumerate(hits, start=1):
        text = hit.chunk.text.replace("\n", " ").replace("|", "\\|")[:110]
        info = (explain or {}).get(hit.chunk.chunk_uid)
        fusion = f"dense#{info['dense_rank']} bm25#{info['bm25_rank']} rrf={info['rrf']}" if info else "—"
        mark = "**GOLD**" if hit.chunk.chunk_uid == q["chunk_id"] else ("also correct" if hit.chunk.chunk_uid in ids else "")
        lines.append(
            f"| {rank} | `{hit.chunk.chunk_uid}` | {hit.chunk.sdk_version} | {hit.dense_score:.3f} | "
            f"{hit.final_score:.3f} | {fusion} | {mark} | {text} |"
        )
    lines += ["", f"**Answer:** `{reply}`", "", f"**Label: {verdict}** — {evidence}", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retriever", choices=sorted(RETRIEVERS), required=True)
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    pages = load_pages(ROOT / "corpus")
    chunks = make_chunks(pages, "structured")
    store = SdkVectorStore()
    store.ingest(COLLECTION, chunks)
    common = common_terms(chunks)
    corpus_ids = {c.chunk_uid for c in chunks}

    build_start = time.perf_counter()
    retriever = RETRIEVERS[args.retriever](store, COLLECTION)
    build_ms = (time.perf_counter() - build_start) * 1000
    # Diagnostic-only deep list, always from the baseline retriever so
    # "where was the gold chunk" means the same thing in both runs.
    diag = BaselineRetriever(store, COLLECTION)

    golden = load_golden()
    for q in golden:  # warm-up: model load, Chroma caches
        retriever.retrieve(q["question"], K)

    samples: dict[str, list[float]] = {q["id"]: [] for q in golden}
    e2e: dict[str, list[float]] = {q["id"]: [] for q in golden}
    for _ in range(LATENCY_REPEATS):
        for q in golden:
            start = time.perf_counter()
            hits = retriever.retrieve(q["question"], K)
            mid = time.perf_counter()
            answer(q["question"], hits, common_terms=common)
            end = time.perf_counter()
            samples[q["id"]].append((mid - start) * 1000)
            e2e[q["id"]].append((end - start) * 1000)

    records, blocks = [], []
    for q in golden:
        hits = retriever.retrieve(q["question"], K)
        deep = diag.retrieve(q["question"], DIAG_DEPTH)
        reply = answer(q["question"], hits, common_terms=common)
        verdict, evidence = label(q, hits, deep, reply, corpus_ids, common)
        rank = first_correct_rank(hits, q)
        records.append({
            "id": q["id"],
            "question": q["question"],
            "gold": q["chunk_id"],
            "hit_at_3": rank > 0,
            "gold_rank": rank,
            "hit_at_3_lenient": first_correct_rank(hits, q, strict=False) > 0,
            "baseline_deep_rank": first_correct_rank(deep, q),
            "top3": [h.chunk.chunk_uid for h in hits],
            "answer": reply,
            "answer_correct": answer_is_correct(reply, q),
            "label": verdict,
            "evidence": evidence,
            "retrieval_ms_median": round(statistics.median(samples[q["id"]]), 2),
        })
        blocks.append(inspection_block(q, hits, reply, verdict, evidence, getattr(retriever, "last_explain", None)))

    all_samples = [s for v in samples.values() for s in v]
    all_e2e = [s for v in e2e.values() for s in v]
    hits_total = sum(r["hit_at_3"] for r in records)
    tally = {lab: sum(1 for r in records if r["label"] == lab) for lab in ("PASS", "R", "G", "NIC")}
    summary = {
        "retriever": args.retriever,
        "questions": len(records),
        "hit_rate_at_3": round(hits_total / len(records), 3),
        "hits": hits_total,
        "hits_lenient": sum(r["hit_at_3_lenient"] for r in records),
        "mrr_at_3": round(sum(1 / r["gold_rank"] for r in records if r["gold_rank"]) / len(records), 3),
        "tally": tally,
        "p50_retrieval_ms": round(statistics.median(all_samples), 2),
        "p95_retrieval_ms": round(statistics.quantiles(all_samples, n=20)[18], 2),
        "p50_end_to_end_ms": round(statistics.median(all_e2e), 2),
        "latency_samples": len(all_samples),
        "index_build_ms": round(build_ms, 1),
    }
    (OUT / f"{args.retriever}.json").write_text(
        json.dumps({"summary": summary, "records": records}, indent=2), encoding="utf-8"
    )
    header = (
        f"# Inspection view — retriever `{args.retriever}`\n\n"
        f"hit-rate@3 = {hits_total}/{len(records)} | tally = {tally} | "
        f"p50 retrieval = {summary['p50_retrieval_ms']} ms\n\n"
    )
    (OUT / f"inspection_{args.retriever}.md").write_text(header + "\n".join(blocks), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in records:
        print(f"{r['id']} hit@3={'Y' if r['hit_at_3'] else 'N'} rank={r['gold_rank']} {r['label']}: {r['evidence']}")


if __name__ == "__main__":
    main()
