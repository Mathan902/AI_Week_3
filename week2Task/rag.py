from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Document:
    text: str
    source: str
    title: str


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str
    title: str
    section: str
    chunk_id: int


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float


class Embedder(Protocol):
    def encode(self, texts: list[str], **kwargs: object) -> np.ndarray: ...


def split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"[ \t]+", " ", text).strip()
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", cleaned) if part.strip()]


def chunk_document(document: Document, chunk_size: int, overlap: int) -> list[Chunk]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Use chunk_size > overlap >= 0")

    sentences = split_sentences(document.text)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_words = 0
    section = document.title

    def add_chunk() -> None:
        if not current:
            return
        chunks.append(
            Chunk(
                text=" ".join(current),
                source=document.source,
                title=document.title,
                section=section,
                chunk_id=len(chunks),
            )
        )

    for sentence in sentences:
        if sentence.startswith("#"):
            section = sentence.lstrip("# ").strip() or section
        words = sentence.split()
        if current and current_words + len(words) > chunk_size:
            add_chunk()
            tail: list[str] = []
            tail_words = 0
            for old_sentence in reversed(current):
                count = len(old_sentence.split())
                if tail_words + count > overlap:
                    break
                tail.insert(0, old_sentence)
                tail_words += count
            current = tail
            current_words = tail_words
        current.append(sentence)
        current_words += len(words)
    add_chunk()
    return chunks


class InMemoryIndex:
    def __init__(self, embedder: Embedder, chunks: list[Chunk]):
        self.embedder = embedder
        self.chunks = chunks
        texts = [chunk.text for chunk in chunks]
        self.embeddings = np.asarray(
            embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        )

    def search(self, question: str, top_k: int = 4) -> list[SearchResult]:
        if not self.chunks:
            return []
        query = np.asarray(
            self.embedder.encode([question], normalize_embeddings=True, show_progress_bar=False)[0],
            dtype=np.float32,
        )
        scores = self.embeddings @ query
        indices = np.argsort(scores)[::-1][: min(top_k, len(scores))]
        return [SearchResult(self.chunks[index], float(scores[index])) for index in indices]


def has_evidence(results: list[SearchResult], threshold: float) -> bool:
    return bool(results) and results[0].score >= threshold


def build_context(results: list[SearchResult]) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        blocks.append(
            f"[SOURCE {index}] {result.chunk.title} | {result.chunk.source} | "
            f"section: {result.chunk.section}\n{result.chunk.text}"
        )
    return "\n\n".join(blocks)


def extractive_answer(results: list[SearchResult]) -> str:
    if not results:
        return "I don't know based on the provided documents."
    sentences = split_sentences(results[0].chunk.text)
    return (" ".join(sentences[:3]) + " [Source 1]").strip()

