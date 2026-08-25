"""Grounded generation, deterministic by design.

The answer stage quotes the fact-bearing lines of the best-matching retrieved
chunk and cites its chunk_uid; refusal is enforced by a two-stage gate
(evidence score + lexical support), not by prompt suggestion. No LLM API is
required, which keeps every transcript reproducible.
"""
from __future__ import annotations

import re

from vector_store import Hit

REFUSAL = "I don't know based on the provided documents."

_STOPWORDS = {
    "the", "and", "for", "with", "how", "what", "which", "when", "does",
    "did", "are", "can", "you", "your", "per", "not", "from", "that", "this",
}


def lexical_support(question: str, hits: list[Hit], top_n: int = 3,
                    common_terms: set[str] | None = None) -> float:
    """Fraction of the question's salient terms found in the top-N chunks.
    Terms that occur in most of the corpus (e.g. 'sdk') carry no signal."""
    tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", question.lower())
        if len(token) > 2 and token not in _STOPWORDS
    ]
    if common_terms:
        tokens = [token for token in tokens if token not in common_terms]
    if not tokens:
        return 1.0
    corpus_text = " ".join(hit.chunk.text.lower() for hit in hits[:top_n])
    found = sum(1 for token in set(tokens) if token in corpus_text)
    return found / len(set(tokens))


def evidence_gate(hits: list[Hit], threshold: float) -> bool:
    return bool(hits) and hits[0].final_score >= threshold


def _keywords(question: str) -> list[str]:
    return [w.lower() for w in re.split(r"[^a-z0-9]+", question.lower()) if len(w) > 2]


def _extractive_cited(question: str, hits: list[Hit]) -> str:
    """Quote the lines of the chunk that best cover the question's terms."""
    keywords = set(_keywords(question))

    def coverage(text: str) -> int:
        return sum(1 for keyword in keywords if keyword in text)

    best = max(hits[:5], key=lambda hit: (coverage(hit.chunk.text), hit.final_score))
    lines = [line.strip() for line in best.chunk.text.splitlines() if line.strip()]
    sentences = [
        sentence.strip()
        for sentence in best.chunk.text.replace("\n", " ").split(". ")
        if sentence.strip()
    ]
    seen: set[str] = set()
    candidates = []
    for candidate in lines + sentences:
        if candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)
    picked = sorted(candidates, key=coverage, reverse=True)[:2]
    return " ".join(picked) + f" [chunk:{best.chunk.chunk_uid}]"


def answer(question: str, hits: list[Hit], threshold: float = 0.40,
           support_floor: float = 0.6, common_terms: set[str] | None = None) -> str:
    if not hits or hits[0].final_score < threshold:
        return REFUSAL
    if lexical_support(question, hits, common_terms=common_terms) < support_floor:
        return REFUSAL
    return _extractive_cited(question, hits)
