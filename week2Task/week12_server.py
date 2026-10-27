"""Week 12: the docs engine's own MCP server (stdio, FastMCP). The capability other squads call.

    .venv/bin/python week12_server.py                 # JSON-RPC on stdin/stdout; launched by an MCP host
    npx @modelcontextprotocol/inspector .venv/bin/python week12_server.py     # a client that isn't ours
    claude mcp add acme-docs -- "$PWD/.venv/bin/python" "$PWD/week12_server.py"  # or Claude Code as the client

Tools (all read-only, no model call anywhere in this file):
  search_docs(query, sdk_version)        Week 3-4 retriever, PINNED to one version by a Chroma metadata filter
  check_deprecation(symbol, sdk_version) changelog lookup: removed / renamed / default changed, and in which version
  symbol_exists(symbol, sdk_version)     the per-version symbol table (week12_guards.SYMBOLS), built from the docs
  get_openapi_spec(path)                 the v3 OpenAPI operations for one path
Resource: docs://version-support-matrix

Trace propagation: a host that sends `_meta: {"trace_id": ...}` on tools/call gets that id on the server-side span
(week12/logs/mcp_server-YYYY-MM-DD.jsonl) and echoed back in the result's `_trace`. A client that sends none (the
Inspector, Claude Code) gets a fresh server-minted id, so every call is still traceable. Arguments are redacted
before they are logged.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError

import week12_guards as g

ROOT = Path(__file__).parent
LOG_DIR = Path(os.environ.get("W12_LOG_DIR") or ROOT / "week12" / "logs")
COLLECTION = "w12_docs"
TOP_K = 3

mcp = FastMCP("acme-docs", instructions=(
    "Acme Python SDK documentation for BOTH live major versions (v2.x and v3.x are both supported; ~40% of "
    "integrators are on v2). Every tool takes the caller's sdk_version: pass the version the caller's code RUNS ON, "
    "e.g. '2.4' or '3.0', never a default. Read-only."))

_store = None


def store():
    """The Week 3-4 structure-aware chunks in an in-process Chroma, so parallel servers never share a collection."""
    global _store
    if _store is None:
        import chromadb
        from chunking import load_pages, make_chunks
        from vector_store import SdkVectorStore
        with contextlib.redirect_stdout(sys.stderr):  # stdout is the JSON-RPC channel
            s = SdkVectorStore.__new__(SdkVectorStore)
            from sentence_transformers import SentenceTransformer
            from vector_store import EMBED_MODEL
            s.client = chromadb.EphemeralClient()
            s.embedder = SentenceTransformer(EMBED_MODEL)
            s.ingest(COLLECTION, make_chunks(load_pages(ROOT / "corpus"), "structured"))
        _store = s
    return _store


def _major(sdk_version: str) -> tuple[str | None, str]:
    raw = str(sdk_version or "").strip()
    mm = g._major_minor(raw if raw.lower().startswith("v") else f"v{raw}")
    return (mm[0], mm[1]) if mm else (None, raw)


def _require_version(sdk_version: str) -> tuple[str, str]:
    major, minor = _major(sdk_version)
    if major in g.PUBLISHED:
        return major, minor
    asked = f"{minor}" if major else repr(sdk_version)
    raise ToolError(
        f"no docs for SDK {asked}. Published docs: v2 (SDK {g.PUBLISHED['v2']['covers']}, still supported) and v3 "
        f"(SDK {g.PUBLISHED['v3']['covers']}, current). Pass the version the caller's code runs on, e.g. "
        f"sdk_version=\"2.4\" or \"3.0\". If the caller named a version that does not exist (e.g. 4.x), say so and "
        f"answer for {g.LATEST}; do not guess an API.")


def _log(tool: str, args: dict, ctx: Context | None, t0: float, result: dict | None, error: str | None) -> dict:
    meta = ctx.request_context.meta if ctx is not None else None
    trace_id = getattr(meta, "trace_id", None) if meta is not None else None
    span = {"trace_id": trace_id or "srv-" + uuid.uuid4().hex[:12], "trace_from": "host" if trace_id else "server",
            "parent_span": getattr(meta, "parent_span", None) if meta is not None else None,
            "span": f"mcp.server.{tool}", "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1), "cost_usd": 0.0,
            "args": g.redact_obj(args), "error": error,
            "result_ids": [r["chunk_id"] for r in (result or {}).get("results", [])]}
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / f"mcp_server-{span['ts'][:10]}.jsonl").open("a") as fh:
        fh.write(json.dumps(g.redact_obj(span)) + "\n")
    return span


def _traced(tool: str, args: dict, ctx: Context | None, fn):
    t0 = time.perf_counter()
    try:
        result = fn()
    except ToolError as exc:
        _log(tool, args, ctx, t0, None, str(exc))
        raise
    span = _log(tool, args, ctx, t0, result, None)
    return {**result, "_trace": {"trace_id": span["trace_id"], "span": span["span"], "latency_ms": span["latency_ms"]}}


# ---------------------------------------------------------------- tools

@mcp.tool()
def search_docs(query: str, sdk_version: str, ctx: Context = None) -> dict:
    """Semantic search over the Acme Python SDK docs of ONE version, enforced by a metadata filter: a v2 search can
    only return v2 pages and a v3 search only v3 pages. Returns the 3 best chunks with chunk_id, the SDK version the
    page belongs to, and a link to the page section. Cite the chunk_id.

    When to use: how-to, parameter and behaviour questions for the caller's version.
    When NOT to use: "was X removed / renamed?" (check_deprecation) or "does method X exist in my version?"
    (symbol_exists).

    sdk_version: the version the caller's code RUNS ON, e.g. "2.4" or "3.0" ("v2"/"v3" also accepted). v2 and v3 are
    both live; do not default to v3 for a v2 caller. For a migration, search the v3 docs for the new code.
    """
    def run():
        major, minor = _require_version(sdk_version)
        with contextlib.redirect_stdout(sys.stderr):
            hits = store().search(COLLECTION, query, top_k=TOP_K, filters={"sdk_version": major})
        return {"sdk_version": major, "covers": g.PUBLISHED[major]["covers"], "filter": {"sdk_version": major},
                "results": [{"chunk_id": h.chunk.chunk_uid, "sdk_version": h.chunk.sdk_version,
                             "page": f"corpus/sdk_{h.chunk.sdk_version}/{h.chunk.source_file}",
                             "section": h.chunk.section,
                             "url": f"corpus/sdk_{h.chunk.sdk_version}/{h.chunk.source_file}{h.chunk.anchor}",
                             "score": round(h.final_score, 3), "text": h.chunk.text} for h in hits]}
    return _traced("search_docs", {"query": query, "sdk_version": sdk_version}, ctx, run)


@mcp.tool()
def check_deprecation(symbol: str, sdk_version: str, ctx: Context = None) -> dict:
    """Look up ONE SDK symbol (method, exception, constructor option) in the v2->v3 changelog. Returns whether it was
    removed, renamed or had its default changed, the version that change landed in (changed_in), the replacement,
    and what that means for code running on sdk_version. Use it on every v2 name you are about to put in an answer:
    a v2 caller should be told what will break when they upgrade, without having to ask. A symbol the changelog does
    not mention returns status 'not_in_changelog' (that does NOT mean it exists: use symbol_exists).
    """
    def run():
        major, minor = _require_version(sdk_version)
        e = g.changelog_entry(symbol)
        if not e:
            return {"symbol": symbol, "sdk_version": major, "status": "not_in_changelog"}
        out = {k: e[k] for k in ("symbol", "status", "kind", "changed_in", "deprecated_in", "replacement",
                                 "replacement_path", "note", "source")}
        if major == "v2":
            out["for_caller"] = (f"works on {minor}; {e['kind']} in {e['changed_in']}: when upgrading use "
                                 f"{e['replacement']}")
        else:
            out["for_caller"] = (f"{e['kind']} in {e['changed_in']}: "
                                 + (f"`{e['symbol']}` no longer exists on {minor}; use {e['replacement']}"
                                    if e["status"] in ("removed", "renamed") else e["replacement"]))
        return {"sdk_version": major, **out}
    return _traced("check_deprecation", {"symbol": symbol, "sdk_version": sdk_version}, ctx, run)


@mcp.tool()
def symbol_exists(symbol: str, sdk_version: str, ctx: Context = None) -> dict:
    """Check whether ONE name is part of the SDK in the caller's version: a client method (client.send,
    files.upload), an importable name (RateLimitError, verify_signature) or a Client constructor option
    (timeout_ms). Returns exists true/false, the documented parameters, and whether it exists in the other major
    version instead. Call it before putting any method you are not sure of into a code sample; never write a
    signature the docs do not show.
    """
    def run():
        major, minor = _require_version(sdk_version)
        other = next(v for v in g.PUBLISHED if v != major)
        found = g.SYMBOLS[major].exists(symbol)
        elsewhere = g.SYMBOLS[other].exists(symbol)
        out = {"sdk_version": major, **found,
               f"exists_in_{other}": elsewhere["exists"]}
        e = g.changelog_entry(symbol)
        if not found["exists"] and e:
            out["changelog"] = f"{e['kind']} in {e['changed_in']}; use {e['replacement']}"
        return out
    return _traced("symbol_exists", {"symbol": symbol, "sdk_version": sdk_version}, ctx, run)


@mcp.tool()
def get_openapi_spec(path: str, ctx: Context = None) -> dict:
    """Return the OpenAPI operations (HTTP method, parameters, and the SDK call x-sdk-call) for ONE exact endpoint
    path of the v3 API, e.g. /v3/invoices. v3 only; it does not search prose docs and knows nothing about v2."""
    def run():
        p = path.strip().rstrip("/")
        if p not in g.SPEC["paths"]:
            raise ToolError(f"{p} is not a path in the v3 API; paths are {sorted(g.SPEC['paths'])}")
        return {"path": p, "sdk_version": "v3", "operations": g.SPEC["paths"][p]}
    return _traced("get_openapi_spec", {"path": path}, ctx, run)


@mcp.resource("docs://version-support-matrix", name="version-support-matrix", mime_type="application/json",
              description="Which SDK major versions have published docs, what they cover, and their status.")
def version_support_matrix() -> str:
    return json.dumps({"published_docs": g.PUBLISHED, "latest": g.LATEST})


if __name__ == "__main__":
    store()  # load the embedder + index before serving: lazily, the first search_docs paid ~8 s (seam S4)
    mcp.run("stdio")
