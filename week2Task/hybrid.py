from __future__ import annotations

import math
import re
from collections import Counter

from vector_store import LEXICAL_BOOST, Hit, SdkVectorStore

RRF_K = 60
CANDIDATE_DEPTH = 25
BM25_K1 = 1.5
BM25_B = 0.75

_WORD_RE = re.compile(r"[a-z0-9_]+(?:[.\-][a-z0-9_]+)*")
_PART_RE = re.compile(r"[._\-]")


def bm25_tokens(text: str) -> list[str]:
    """Keep identifiers whole (`retry_backoff_ms`, `x-ratelimit-remaining`, `v3.0`)
    AND emit their parts, so exact symbols match exactly and prose still matches."""
    tokens: list[str] = []
    for word in _WORD_RE.findall(text.lower()):
        tokens.append(word)
        parts = [part for part in _PART_RE.split(word) if part]
        if len(parts) > 1:
            tokens.extend(parts)
    return tokens


class BM25Index:
    def __init__(self, ids: list[str], texts: list[str]):
        self.ids = ids
        self.docs = [Counter(bm25_tokens(text)) for text in texts]
        self.lengths = [sum(doc.values()) for doc in self.docs]
        self.avg_len = sum(self.lengths) / len(self.lengths)
        df: Counter = Counter()
        for doc in self.docs:
            df.update(doc.keys())
        n = len(self.docs)
        self.idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def search(self, query: str, top_k: int) -> list[str]:
        terms = [term for term in set(bm25_tokens(query)) if term in self.idf]
        scored = []
        for index, doc in enumerate(self.docs):
            norm = BM25_K1 * (1 - BM25_B + BM25_B * self.lengths[index] / self.avg_len)
            score = sum(
                self.idf[term] * doc[term] * (BM25_K1 + 1) / (doc[term] + norm)
                for term in terms
                if doc[term]
            )
            if score > 0:
                scored.append((score, index))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [self.ids[index] for _, index in scored[:top_k]]


def rrf_fuse(rankings: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, uid in enumerate(ranking, start=1):
            scores[uid] = scores.get(uid, 0.0) + 1.0 / (k + rank)
    # ties broken by position in the first (dense) ranking, then id, for determinism
    first = {uid: pos for pos, uid in enumerate(rankings[0])}
    return sorted(scores.items(), key=lambda item: (-item[1], first.get(item[0], 10**9), item[0]))


class HybridRetriever:
    name = "hybrid"

    def __init__(self, store: SdkVectorStore, collection: str):
        self.store = store
        self.collection = collection
        data = store.client.get_collection(collection).get(include=["documents", "metadatas"])
        self.chunks = {
            uid: store._chunk(uid, document, meta)
            for uid, document, meta in zip(data["ids"], data["documents"], data["metadatas"])
        }
        self.bm25 = BM25Index(data["ids"], data["documents"])
        self.last_explain: dict[str, dict] = {}

    def retrieve(self, query: str, k: int) -> list[Hit]:
        dense_hits = self.store.search(self.collection, query, top_k=CANDIDATE_DEPTH)
        dense_ids = [hit.chunk.chunk_uid for hit in dense_hits]
        sparse_ids = self.bm25.search(query, CANDIDATE_DEPTH)
        fused = rrf_fuse([dense_ids, sparse_ids])[:k]

        by_uid = {hit.chunk.chunk_uid: hit for hit in dense_hits}
        hits = []
        for uid, _ in fused:
            if uid not in by_uid:  # BM25-only candidate: score it the baseline way for the gate
                by_uid[uid] = self._baseline_scored(query, uid)
            hits.append(by_uid[uid])
        self.last_explain = {
            uid: {
                "dense_rank": dense_ids.index(uid) + 1 if uid in dense_ids else None,
                "bm25_rank": sparse_ids.index(uid) + 1 if uid in sparse_ids else None,
                "rrf": round(score, 5),
            }
            for uid, score in fused
        }
        return hits

    def _baseline_scored(self, query: str, uid: str) -> Hit:
        col = self.store.client.get_collection(self.collection)
        stored = col.get(ids=[uid], include=["embeddings"])["embeddings"][0]
        query_vec = self.store._embed([query])[0]
        dense = float(sum(a * b for a, b in zip(stored, query_vec)))
        lexical = self.store._lexical_overlap(query, self.chunks[uid].text)
        return Hit(chunk=self.chunks[uid], dense_score=dense, final_score=dense + LEXICAL_BOOST * lexical)
