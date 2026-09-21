"""Week 5: a complete, replayable trace for every request the docs assistant serves.

The shipped pipeline is the Week 4 baseline (dense MiniLM + lexical boost over
`sdk_structured`, k=3) feeding the deterministic extractive generator in
`generate.py`. There is no LLM and no prompt template, so the "prompt version"
is the generator version: a hash of generate.py plus its gate parameters.

One JSON object per line in week5/traces.jsonl. A trace is enough to replay the
answer from the trace alone: `replay_generation()` rebuilds the retrieved hits
from the stored chunk text + scores and re-runs `generate.answer()`;
`replay_full()` additionally re-runs retrieval from the stored query + params.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from chunking import Chunk, load_pages, make_chunks
from generate import answer
from run_eval import common_terms
from vector_store import EMBED_MODEL, LEXICAL_BOOST, Hit, SdkVectorStore

ROOT = Path(__file__).parent
TRACE_FILE = ROOT / "week5" / "traces.jsonl"
COLLECTION = "sdk_structured"
TOP_K = 3
THRESHOLD = 0.40
SUPPORT_FLOOR = 0.6
TRACE_SCHEMA = 1  # before this, week4_output/*.json kept only top-3 ids + answer; see week5/notes.md


def _sha(path_or_text: Path | str) -> str:
    data = path_or_text.read_bytes() if isinstance(path_or_text, Path) else path_or_text.encode()
    return hashlib.sha256(data).hexdigest()[:12]


def _model_revision() -> str:
    ref = (Path.home() / ".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"
           / "refs" / "main")
    return ref.read_text().strip() if ref.exists() else "unknown"


class TracedAssistant:
    def __init__(self, trace_file: Path = TRACE_FILE) -> None:
        self.trace_file = trace_file
        self.trace_file.parent.mkdir(exist_ok=True)
        chunks = make_chunks(load_pages(ROOT / "corpus"), "structured")
        self.store = SdkVectorStore()
        self.store.ingest(COLLECTION, chunks)
        self.common = common_terms(chunks)
        self.static = {
            "pipeline": "week4-baseline",
            "generator_version": _sha(ROOT / "generate.py"),
            "retriever_version": _sha(ROOT / "vector_store.py"),
            "corpus_version": _sha("".join(_sha(p) for p in sorted((ROOT / "corpus").rglob("*.md")))),
            "model": {"embedder": EMBED_MODEL, "revision": _model_revision(), "generator": "extractive (no LLM)"},
            "params": {
                "collection": COLLECTION, "top_k": TOP_K, "filters": None,
                "lexical_boost": LEXICAL_BOOST, "score_threshold": THRESHOLD,
                "support_floor": SUPPORT_FLOOR,
            },
            "common_terms": sorted(self.common),
        }

    def ask(self, question: str, session: str | None = None) -> dict:
        start = time.perf_counter()
        hits = self.store.search(COLLECTION, question, top_k=TOP_K)
        mid = time.perf_counter()
        reply = answer(question, hits, threshold=THRESHOLD, support_floor=SUPPORT_FLOOR,
                       common_terms=self.common)
        end = time.perf_counter()
        trace = {
            "trace_id": "tr-" + uuid.uuid4().hex[:10],
            "schema": TRACE_SCHEMA,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session": session,
            "question": question,
            **self.static,
            "retrieved": [
                {
                    "rank": rank, "chunk_id": h.chunk.chunk_uid, "sdk_version": h.chunk.sdk_version,
                    "dense": round(h.dense_score, 6), "final": round(h.final_score, 6),
                    "text": h.chunk.text, "meta": {
                        "source_file": h.chunk.source_file, "page_id": h.chunk.page_id,
                        "page_type": h.chunk.page_type, "section": h.chunk.section,
                        "anchor": h.chunk.anchor,
                    },
                }
                for rank, h in enumerate(hits, start=1)
            ],
            "raw_output": reply,
            "latency_ms": {"retrieve": round((mid - start) * 1000, 2),
                           "generate": round((end - mid) * 1000, 2)},
        }
        with self.trace_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(trace) + "\n")
        return trace


def load_traces(path: Path = TRACE_FILE) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def hits_from_trace(trace: dict) -> list[Hit]:
    return [
        Hit(
            chunk=Chunk(text=r["text"], chunk_uid=r["chunk_id"], sdk_version=r["sdk_version"], **r["meta"]),
            dense_score=r["dense"], final_score=r["final"],
        )
        for r in trace["retrieved"]
    ]


def replay_generation(trace: dict) -> str:
    """Re-run the answer stage using nothing but the trace."""
    p = trace["params"]
    return answer(trace["question"], hits_from_trace(trace), threshold=p["score_threshold"],
                  support_floor=p["support_floor"], common_terms=set(trace["common_terms"]))


def replay_full(trace: dict, store: SdkVectorStore) -> tuple[list[Hit], str]:
    """Re-run retrieval + generation from the trace's query and params."""
    p = trace["params"]
    hits = store.search(p["collection"], trace["question"], top_k=p["top_k"], filters=p["filters"])
    reply = answer(trace["question"], hits, threshold=p["score_threshold"],
                   support_floor=p["support_floor"], common_terms=set(trace["common_terms"]))
    return hits, reply
