"""Runs the full Task Set E measurement and writes eval_output/ artifacts.

Scope: indexes ONLY corpus/sdk_v2 + corpus/sdk_v3 (the new drop), not the
whole docs site.
"""
from __future__ import annotations

import json
from pathlib import Path

from chunking import load_pages, make_chunks
from generate import REFUSAL, answer
from questions import GOLD_QUESTIONS, REFUSAL_CASES
from vector_store import SdkVectorStore

ROOT = Path(__file__).parent
OUT = ROOT / "eval_output"
STRATEGIES = ("naive", "structured")
CITED_PICKS = (1, 4, 6)
FILTER_QUERY = "What is the default retry backoff delay between retries?"


def common_terms(chunks) -> set[str]:
    """Terms appearing in over 40% of chunks carry no discriminative signal."""
    total = len(chunks)
    counts: dict[str, int] = {}
    for chunk in chunks:
        for token in set(chunk.text.lower().split()):
            counts[token] = counts.get(token, 0) + 1
    return {term for term, count in counts.items() if count / total > 0.4}


def gold_rank(hits, gold) -> int:
    """1-based rank of the first chunk carrying the known answer, else 0."""
    for rank, hit in enumerate(hits, start=1):
        if hit.chunk.page_id == gold.gold_page_id and all(
            fact.lower() in hit.chunk.text.lower() for fact in gold.answer_facts
        ):
            return rank
    return 0


def is_hit(hits, gold) -> bool:
    return gold_rank(hits, gold) > 0


def fmt_hits(hits) -> str:
    return "\n".join(
        f"  {rank}. [{hit.chunk.sdk_version}] {hit.chunk.page_id} "
        f"{hit.chunk.anchor} | dense={hit.dense_score:.3f} final={hit.final_score:.3f} "
        f"| chunk_uid={hit.chunk.chunk_uid}"
        for rank, hit in enumerate(hits, start=1)
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    pages = load_pages(ROOT / "corpus")
    store = SdkVectorStore()
    collections, counts = {}, {}
    common = {}
    cluster_summaries = {}
    for strategy in STRATEGIES:
        chunks = make_chunks(pages, strategy)
        collection = f"sdk_{strategy}"
        counts[strategy] = store.ingest(collection, chunks)
        collections[strategy] = collection
        common[strategy] = common_terms(chunks)
        cluster_summaries[strategy] = store.create_clusters(collection)

    report: list[str] = []
    per_question = {}

    for strategy in STRATEGIES:
        report.append(
            f"\n# Clusters [{strategy}]\n\n"
            f"k={cluster_summaries[strategy]['k']} "
            f"(silhouette={cluster_summaries[strategy]['silhouette']})\n\n"
            f"| cluster | chunks |\n|---|---|\n" + "".join(
                f"| {name} | {size} |\n"
                for name, size in cluster_summaries[strategy]["sizes"].items()
            )
        )

    report.append("# Search-only dump — 8 questions x 2 strategies\n")
    report.append(f"Indexed chunks: {json.dumps(counts)}\n")
    for gold in GOLD_QUESTIONS:
        row = {}
        report.append(
            f"\n## Q{gold.number}. {gold.question}\n"
            f"- Known answer: `{gold.gold_page_id}` -> {gold.gold_section} "
            f"(depends on {gold.depends_on})\n"
        )
        for strategy in STRATEGIES:
            hits = store.search(collections[strategy], gold.question, top_k=5)
            rank = gold_rank(hits, gold)
            row[strategy] = {
                "hit": rank > 0,
                "gold_rank": rank,
                "top1_page": hits[0].chunk.page_id if hits else None,
                "top5": [
                    {"page_id": h.chunk.page_id, "anchor": h.chunk.anchor,
                     "dense": round(h.dense_score, 3), "final": round(h.final_score, 3),
                     "chunk_uid": h.chunk.chunk_uid}
                    for h in hits
                ],
            }
            report.append(
                f"- **{strategy}** hit-in-top-5: {'YES' if rank else 'NO'} "
                f"(gold at rank {rank or '-'}, top-1 was {row[strategy]['top1_page']})"
            )
            report.append("```")
            report.append(fmt_hits(hits))
            report.append("```")
        per_question[gold.number] = row

    totals = {
        s: sum(1 for row in per_question.values() if row[s]["hit"]) for s in STRATEGIES
    }
    quality = {}
    for strategy in STRATEGIES:
        ranks = [row[strategy]["gold_rank"] for row in per_question.values()]
        quality[strategy] = {
            "top1_is_gold": sum(1 for r in ranks if r == 1),
            "mrr": round(sum(1 / r for r in ranks if r) / len(ranks), 3),
        }

    # --- structural & staleness diagnostics ---
    diagnostics = {}
    all_chunks = {s: make_chunks(pages, s) for s in STRATEGIES}
    for strategy in STRATEGIES:
        broken_fences = sum(
            1 for chunk in all_chunks[strategy]
            if chunk.text.count("```") % 2 == 1
        )
        diagnostics[strategy] = {"broken_code_fences": broken_fences}
    for strategy in STRATEGIES:
        stale = sum(
            1 for row in per_question.values()
            if row[strategy]["top5"]
            and row[strategy]["top5"][0]["page_id"].startswith("v2")
        )
        diagnostics[strategy]["stale_v2_top1"] = stale
        report.append(
            f"\nDiagnostic [{strategy}]: broken_code_fences="
            f"{diagnostics[strategy]['broken_code_fences']}, "
            f"queries_where_top1_is_stale_v2={stale}"
        )

    # --- metadata filter demo: find a real query where v2 outranks v3 unfiltered ---
    filter_candidates = (
        "What happens when the API returns HTTP 429?",
        "How many automatic retries does the client make by default?",
        "What exception is raised for too many requests?",
        FILTER_QUERY,
        "What is the default request timeout for the client?",
    )
    filter_demo, demo_query = {}, None
    for candidate in filter_candidates:
        unfiltered = store.search(collections["structured"], candidate, top_k=5)
        if not unfiltered or unfiltered[0].chunk.sdk_version != "v2":
            continue
        filtered = store.search(
            collections["structured"], candidate, top_k=5,
            filters={"sdk_version": "v3"},
        )
        if filtered[0].chunk.sdk_version == "v3":
            demo_query = candidate
            filter_demo = {"unfiltered_top1": unfiltered[0].chunk.page_id,
                           "filtered_top1": filtered[0].chunk.page_id}
            report.append(f"\n# Metadata filter demo\n\nQuery: {candidate}\n")
            report.append("\n## Unfiltered top-5\n```" + fmt_hits(unfiltered) + "\n```")
            report.append("\n## Filtered sdk_version=v3 top-5\n```" + fmt_hits(filtered) + "\n```")
            break
    if demo_query is None:
        report.append("\n# Metadata filter demo: no qualifying query found")

    # --- cited answers & refusals (generation stage pins sdk_version=v3,
    # because these questions ask about v3; the unfiltered bug is shown above) ---
    report.append("\n# Generation transcripts\n")
    gen_out = {"cited": [], "refusals": []}
    for num in CITED_PICKS:
        gold = next(g for g in GOLD_QUESTIONS if g.number == num)
        hits = store.search(
            collections["structured"], gold.question, top_k=5,
            filters={"sdk_version": "v3"},
        )
        reply = answer(gold.question, hits, common_terms=common["structured"])
        gen_out["cited"].append({"question": gold.question, "answer": reply})
        report.append(f"\n## Answerable Q{num}: {gold.question}\n```\n{reply}\n```")
    for case in REFUSAL_CASES:
        hits = store.search(
            collections["structured"], case.question, top_k=5,
            filters={"sdk_version": "v3"},
        )
        reply = answer(case.question, hits, common_terms=common["structured"])
        refused = reply == REFUSAL
        gen_out["refusals"].append({
            "question": case.question, "answer": reply, "refused": refused,
            "why": case.why_unanswerable,
        })
        report.append(
            f"\n## Unanswerable: {case.question}\n- Why: {case.why_unanswerable}\n"
            f"- Refused correctly: {'YES' if refused else 'NO'}\n```\n{reply}\n```"
        )

    data = {
        "totals": totals,
        "quality": quality,
        "diagnostics": diagnostics,
        "clusters": cluster_summaries,
        "counts": counts,
        "per_question": per_question,
        "filter_demo": filter_demo,
        "generation": gen_out,
    }
    (OUT / "results_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (OUT / "search_dump.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(totals), json.dumps(quality), "| chunks:", json.dumps(counts))
    print("clusters:", json.dumps(cluster_summaries))
    print("filter demo:", json.dumps(filter_demo))
    print("refusals:", [(r["question"], r["refused"]) for r in gen_out["refusals"]])


if __name__ == "__main__":
    main()
