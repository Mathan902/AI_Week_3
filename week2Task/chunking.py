"""Page parsing and the two chunking strategies under comparison."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageMeta:
    source_file: str
    page_id: str
    sdk_version: str
    page_type: str


@dataclass(frozen=True)
class Chunk:
    text: str
    source_file: str
    page_id: str
    sdk_version: str
    page_type: str
    section: str
    anchor: str
    chunk_uid: str


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_META_RE = re.compile(r"^([a-z_]+):\s*(.+)$")
_ANCHOR_RE = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    return _ANCHOR_RE.sub("-", text.lower()).strip("-")


def parse_page(path: Path) -> tuple[str, PageMeta]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    meta_values: dict[str, str] = {}
    body_start = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _META_RE.match(stripped)
        if match and match.group(1) in {"page_id", "sdk_version", "page_type"}:
            meta_values[match.group(1)] = match.group(2).strip()
            body_start = index + 1
        elif meta_values:
            break
        else:
            break
    missing = {"page_id", "sdk_version", "page_type"} - meta_values.keys()
    if missing:
        raise ValueError(f"{path.name}: missing metadata {sorted(missing)}")
    meta = PageMeta(
        source_file=path.name,
        page_id=meta_values["page_id"],
        sdk_version=meta_values["sdk_version"],
        page_type=meta_values["page_type"],
    )
    return "\n".join(lines[body_start:]).strip() + "\n", meta


def _blocks(section_text: str) -> list[tuple[str, list[str]]]:
    """Split a section into atomic blocks: paragraphs, tables, code fences.
    A table block keeps its header row because header and separator rows are
    adjacent markdown lines; a fence block spans opening to closing triple backtick."""
    lines = section_text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] = []
    kind = "paragraph"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if kind != "fence":
                if current:
                    blocks.append((kind, current))
                current, kind = [line], "fence"
            else:
                current.append(line)
                blocks.append((kind, current))
                current, kind = [], "paragraph"
            continue
        if not stripped:
            if current and kind == "paragraph":
                blocks.append((kind, current))
                current = []
            continue
        if stripped.startswith("|"):
            if kind not in ("table", "fence"):
                if current:
                    blocks.append((kind, current))
                current, kind = [], "table"
        elif kind == "table":
            blocks.append(("table", current))
            current, kind = [], "paragraph"
        current.append(line)
    if current:
        blocks.append((kind, current))
    return blocks


def structured_chunks(meta: PageMeta, body: str, max_words: int = 180) -> list[Chunk]:
    """Split only at markdown headings; keep parameter tables (with header rows)
    and fenced code samples intact inside one chunk."""
    chunks: list[Chunk] = []
    section_title = meta.page_id
    section_lines: list[str] = []

    def flush() -> None:
        nonlocal section_lines
        if not section_lines:
            return
        text_of_section = "\n".join(section_lines).strip()
        if not text_of_section:
            section_lines = []
            return
        pieces = _blocks("\n".join(section_lines))
        buffer: list[str] = []
        buffer_words = 0

        def emit() -> None:
            nonlocal buffer, buffer_words
            if buffer:
                anchor = f"{slug(section_title)}"
                uid = f"{meta.page_id}::{anchor}::{len(chunks)}"
                chunks.append(
                    Chunk(
                        text="\n".join(buffer).strip(),
                        source_file=meta.source_file,
                        page_id=meta.page_id,
                        sdk_version=meta.sdk_version,
                        page_type=meta.page_type,
                        section=section_title,
                        anchor=f"#{slug(section_title)}",
                        chunk_uid=uid,
                    )
                )
                buffer, buffer_words = [], 0

        for kind, lines in pieces:
            block_text = "\n".join(lines).strip()
            block_words = len(block_text.split())
            if kind in ("table", "fence"):
                emit()
                anchor = slug(section_title)
                uid = f"{meta.page_id}::{anchor}::{len(chunks)}"
                label = "parameter table" if kind == "table" else "code sample"
                chunks.append(
                    Chunk(
                        text=block_text,
                        source_file=meta.source_file,
                        page_id=meta.page_id,
                        sdk_version=meta.sdk_version,
                        page_type=meta.page_type,
                        section=section_title,
                        anchor=f"#{slug(section_title)}",
                        chunk_uid=uid + ("-table" if kind == "table" else "-code"),
                    )
                )
                continue
            if buffer_words + block_words > max_words and buffer:
                emit()
            buffer.extend(lines)
            buffer_words += block_words
        emit()
        section_lines = []

    for line in body.splitlines():
        header = _HEADER_RE.match(line)
        if header:
            flush()
            section_title = header.group(2).strip()
        else:
            section_lines.append(line)
    flush()
    return chunks


def naive_chunks(meta: PageMeta, body: str, chunk_size: int = 120, overlap: int = 25) -> list[Chunk]:
    """The Week 3 baseline: fixed-size word window with sentence/line splitting.
    Can cut a parameter table row away from its header row and split code fences."""
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|\n+", re.sub(r"[ \t]+", " ", body))
        if part.strip()
    ]
    chunks: list[Chunk] = []
    current: list[str] = []
    current_words = 0
    section = meta.page_id

    def add() -> None:
        if not current:
            return
        anchor = slug(section)
        chunks.append(
            Chunk(
                text=" ".join(current),
                source_file=meta.source_file,
                page_id=meta.page_id,
                sdk_version=meta.sdk_version,
                page_type=meta.page_type,
                section=section,
                anchor=f"#{anchor}",
                chunk_uid=f"{meta.page_id}::{anchor}::n{len(chunks)}",
            )
        )

    for sentence in sentences:
        header = _HEADER_RE.match(sentence)
        if header:
            section = header.group(2).strip() or section
        words = sentence.split()
        if current and current_words + len(words) > chunk_size:
            add()
            tail: list[str] = []
            tail_words = 0
            for old in reversed(current):
                count = len(old.split())
                if tail_words + count > overlap:
                    break
                tail.insert(0, old)
                tail_words += count
            current, current_words = tail, tail_words
        current.append(sentence)
        current_words += len(words)
    add()
    return chunks


def load_pages(corpus_dir: Path) -> list[tuple[PageMeta, str]]:
    pages = []
    for path in sorted(corpus_dir.rglob("*.md")):
        body, meta = parse_page(path)
        pages.append((meta, body))
    return pages


def make_chunks(pages: list[tuple[PageMeta, str]], strategy: str) -> list[Chunk]:
    if strategy == "naive":
        return [chunk for meta, body in pages for chunk in naive_chunks(meta, body)]
    if strategy == "structured":
        return [chunk for meta, body in pages for chunk in structured_chunks(meta, body)]
    raise ValueError(strategy)
