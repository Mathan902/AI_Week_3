"""Chroma-backed retrieval over SDK chunks with metadata filtering and a
lexical rerank pass on top of dense MiniLM embeddings.

Storage is a persistent local Chroma directory (`chroma_data/`) — no server,
no API keys. Collections survive between runs.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from chunking import Chunk

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LEXICAL_BOOST = 0.15
PERSIST_DIR = Path(__file__).parent / "chroma_data"

_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.split(text.lower()) if token]


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    dense_score: float
    final_score: float


class SdkVectorStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=str(PERSIST_DIR))
        self.embedder = SentenceTransformer(EMBED_MODEL)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.embedder.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vectors, dtype=np.float32).tolist()

    def _collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        return self.client.create_collection(name=name, metadata={"hnsw:space": "cosine"})

    @staticmethod
    def _metadata(chunk: Chunk) -> dict:
        return {
            "source_file": chunk.source_file,
            "page_id": chunk.page_id,
            "sdk_version": chunk.sdk_version,
            "page_type": chunk.page_type,
            "section": chunk.section,
            "anchor": chunk.anchor,
        }

    @staticmethod
    def _chunk(uid: str, document: str, meta: dict) -> Chunk:
        return Chunk(
            text=document,
            source_file=meta["source_file"],
            page_id=meta["page_id"],
            sdk_version=meta["sdk_version"],
            page_type=meta["page_type"],
            section=meta["section"],
            anchor=meta["anchor"],
            chunk_uid=uid,
        )

    def ingest(self, collection: str, chunks: list[Chunk]) -> int:
        col = self._collection(collection)
        col.add(
            ids=[chunk.chunk_uid for chunk in chunks],
            embeddings=self._embed([chunk.text for chunk in chunks]),
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._metadata(chunk) for chunk in chunks],
        )
        return len(chunks)

    @staticmethod
    def _where(filters: dict | None) -> dict | None:
        if not filters:
            return None
        conditions = [
            {key: {"$eq": value}} for key, value in filters.items()
        ]
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def _lexical_overlap(query: str, text: str) -> float:
        query_tokens = set(_tokens(query))
        if not query_tokens:
            return 0.0
        text_tokens = set(_tokens(text))
        return len(query_tokens & text_tokens) / len(query_tokens)

    def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        rerank_lexical: bool = True,
    ) -> list[Hit]:
        col = self.client.get_collection(collection)
        count = col.count()
        if count == 0:
            return []
        response = col.query(
            query_embeddings=self._embed([query]),
            n_results=min(top_k * 3 if rerank_lexical else top_k, count),
            where=self._where(filters),
            include=["documents", "metadatas", "distances"],
        )
        hits: list[Hit] = []
        ids = response["ids"][0]
        documents = response["documents"][0]
        metadatas = response["metadatas"][0]
        distances = response["distances"][0]
        for uid, document, meta, distance in zip(ids, documents, metadatas, distances):
            dense = 1.0 - float(distance)  # cosine space: similarity = 1 - distance
            lexical = self._lexical_overlap(query, document)
            final = dense + (LEXICAL_BOOST * lexical if rerank_lexical else 0.0)
            hits.append(
                Hit(
                    chunk=self._chunk(uid, document, meta),
                    dense_score=dense,
                    final_score=final,
                )
            )
        hits.sort(key=lambda hit: hit.final_score, reverse=True)
        return hits[:top_k]

    # ---------- clustering ----------

    _STOPWORDS = {
        "the", "and", "for", "with", "not", "are", "you", "your", "this",
        "that", "from", "when", "set", "use", "only", "per", "into", "each",
    }

    def create_clusters(self, collection: str, max_k: int = 8) -> dict:
        """KMeans over the stored chunk embeddings; k chosen by silhouette score.
        Every record's metadata gains cluster_id and cluster_label, so retrieval
        can filter by topic cluster like any other field."""
        col = self.client.get_collection(collection)
        data = col.get(include=["embeddings", "metadatas"])
        ids = data["ids"]
        n = len(ids)
        if n < 4:
            raise ValueError(f"{collection}: need >=4 chunks to cluster, got {n}")
        vectors = np.asarray(data["embeddings"], dtype=np.float32)

        best_k, best_labels, best_score = 2, None, -1.0
        for k in range(2, min(max_k, n - 1) + 1):
            labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(vectors)
            score = float(silhouette_score(vectors, labels))
            if score > best_score:
                best_k, best_labels, best_score = k, labels, score

        all_counts: Counter = Counter()
        texts = [meta_or_doc for meta_or_doc in data["metadatas"]]
        for meta in texts:
            all_counts.update(
                token for token in _tokens(str(meta.get("section", "")))
                if len(token) > 2
            )

        cluster_texts: dict[int, int] = {}
        for label in best_labels:
            cluster_texts[int(label)] = cluster_texts.get(int(label), 0) + 1

        names: dict[int, str] = {}
        for cluster_id in sorted(cluster_texts):
            member_metas = [
                meta for meta, label in zip(texts, best_labels) if int(label) == cluster_id
            ]
            counts: Counter = Counter()
            for meta in member_metas:
                counts.update(
                    token for token in _tokens(meta["page_id"])
                    if len(token) > 3
                )
                counts.update(
                    token for token in _tokens(meta.get("section", "").lower())
                    if len(token) > 3 and token not in SdkVectorStore._STOPWORDS
                )
            distinctive = sorted(counts, key=counts.get, reverse=True)[:3]
            names[cluster_id] = "-".join(distinctive) if distinctive else "misc"

        for cluster_id, name in names.items():
            member_ids = [uid for uid, label in zip(ids, best_labels) if int(label) == cluster_id]
            col.update(
                ids=member_ids,
                metadatas=[
                    {
                        "cluster_id": cluster_id,
                        "cluster_label": f"c{cluster_id}-{name}",
                    }
                ]
                * len(member_ids),
            )

        return {
            "k": best_k,
            "silhouette": round(best_score, 3),
            "sizes": {names[c]: size for c, size in sorted(cluster_texts.items())},
        }

    def search_cluster(
        self,
        collection: str,
        query: str,
        cluster_id: int,
        top_k: int = 5,
    ) -> list[Hit]:
        """Retrieve restricted to one topic cluster."""
        return self.search(
            collection, query, top_k=top_k,
            filters={"cluster_id": cluster_id},
        )
