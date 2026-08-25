"""One-time ingestion: chunk the SDK corpus and store it in ChromaDB.

Storage is a persistent local directory (`chroma_data/`) — no server or API
keys required. Re-running is safe; collections are rebuilt from scratch.

Usage:
    .venv\\Scripts\\python.exe ingest.py
"""
from __future__ import annotations

from pathlib import Path

from chunking import load_pages, make_chunks
from vector_store import PERSIST_DIR, SdkVectorStore

ROOT = Path(__file__).parent
STRATEGIES = ("naive", "structured")


def main() -> None:
    store = SdkVectorStore()
    pages = load_pages(ROOT / "corpus")
    print(f"Loaded {len(pages)} pages from corpus/")
    print(f"Persisting to {PERSIST_DIR.resolve()}")

    for strategy in STRATEGIES:
        chunks = make_chunks(pages, strategy)
        collection = f"sdk_{strategy}"
        stored = store.ingest(collection, chunks)
        clusters = store.create_clusters(collection)
        versions = sorted({chunk.sdk_version for chunk in chunks})
        print(
            f"[{collection}] stored {stored} chunks (sdk_version={versions}) | "
            f"clusters k={clusters['k']} silhouette={clusters['silhouette']}"
        )

    print(f"Done. Collections: {[c.name for c in store.client.list_collections()]}")


if __name__ == "__main__":
    main()
