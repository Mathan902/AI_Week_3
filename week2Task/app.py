from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from sentence_transformers import SentenceTransformer

from rag import Document, InMemoryIndex, build_context, chunk_document, extractive_answer, has_evidence


ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "documents"
CONFIGS = {
    "Small: 120 words / 25 overlap": (120, 25),
    "Large: 300 words / 60 overlap": (300, 60),
}
SAMPLE_QUESTIONS = {
    "Customer support": "How long does a customer have to report a damaged parcel?",
    "Recipes & food": "How can the lentil stew be made less spicy?",
    "HR policy": "How many remote-work days can an employee use each week?",
    "Insurance claims": "When must photographs for a water-damage claim be submitted?",
    "Developer documentation": "What happens when the SDK receives HTTP status 429?",
    "Legal contracts": "How much notice is required to terminate for convenience?",
    "Not in documents": "What is the company's office Wi-Fi password?",
}


st.set_page_config(page_title="Ask Six Documents", page_icon="🔎", layout="wide")


@st.cache_resource
def load_embedder() -> SentenceTransformer:
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


@st.cache_resource
def build_indexes() -> dict[str, tuple[InMemoryIndex, int]]:
    documents = [
        Document(path.read_text(encoding="utf-8"), path.name, path.stem.replace("_", " ").title())
        for path in sorted(DOCS_DIR.glob("*.md"))
    ]
    embedder = load_embedder()
    indexes = {}
    for label, (size, overlap) in CONFIGS.items():
        chunks = [chunk for doc in documents for chunk in chunk_document(doc, size, overlap)]
        indexes[label] = (InMemoryIndex(embedder, chunks), len(chunks))
    return indexes


def generate_answer(question: str, context: str, results) -> str:
    return extractive_answer(results)


st.title("Ask Six Documents")
st.caption("Dense retrieval with in-memory embeddings — no vector database")

try:
    indexes = build_indexes()
except Exception as exc:
    st.error(f"Could not load the embedding model: {exc}")
    st.stop()

with st.sidebar:
    st.header("Retrieval settings")
    config = st.radio("Chunking strategy", list(CONFIGS))
    top_k = st.slider("Top-K chunks", 1, 8, 4)
    threshold = st.slider("Evidence threshold", 0.0, 1.0, 0.36, 0.01)
    st.metric("Indexed chunks", indexes[config][1])
    st.caption("Embeddings are stored only in this process's memory.")

selected = st.selectbox("Try a prepared question", list(SAMPLE_QUESTIONS))
question = st.text_input("Question", value=SAMPLE_QUESTIONS[selected])

if st.button("Search and answer", type="primary", disabled=not question.strip()):
    index, _ = indexes[config]
    results = index.search(question, top_k)
    supported = has_evidence(results, threshold)

    st.subheader("Answer")
    if supported:
        with st.spinner("Writing from retrieved evidence..."):
            st.write(generate_answer(question, build_context(results), results))
    else:
        st.warning("I don't know based on the provided documents.")

    st.subheader("Retrieved evidence")
    for rank, result in enumerate(results, start=1):
        with st.expander(f"{rank}. {result.chunk.title} — score {result.score:.3f}"):
            st.write(result.chunk.text)
            st.caption(
                f"Source: {result.chunk.source} | Section: {result.chunk.section} | "
                f"Chunk: {result.chunk.chunk_id}"
            )

    st.subheader("Chunking comparison")
    rows = []
    for label, (candidate_index, count) in indexes.items():
        candidate = candidate_index.search(question, 1)
        rows.append(
            {
                "Strategy": label,
                "Total chunks": count,
                "Best score": round(candidate[0].score, 3) if candidate else 0,
                "Best source": candidate[0].chunk.source if candidate else "None",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

