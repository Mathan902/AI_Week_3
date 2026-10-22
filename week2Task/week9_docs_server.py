"""Week 9: server ONE, our own docs-search MCP server (stdio, FastMCP).

    .venv/bin/python week9_docs_server.py            # speaks JSON-RPC on stdin/stdout; launched by the host

It exposes the three Week 7 tools over MCP, plus the version-support matrix as a RESOURCE: the matrix is
context the host attaches to the prompt, not something the model should spend a turn fetching.

There is no model call anywhere in this file. The server exposes capabilities; the host runs the model.

DOCS_PROMPTS=v1 (set in the host's MCP config env) brings back the first version of search_docs: a one-line
docstring and an opaque "Error 3" for an unpublished version. The default is v2: the docstring is written as
a prompt and the unknown-version path is recoverable. error_before_after.md compares the two.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

import week7_tools as w7

PROMPTS = os.environ.get("DOCS_PROMPTS", "v2")

# What the docs site has published. The registry server knows package versions; this server only knows docs.
PUBLISHED = {"v2": {"covers": "2.x (last 2.9)", "status": "deprecated, security fixes only"},
             "v3": {"covers": "3.x (3.0 to 3.2)", "status": "current"}}
LATEST = "v3"

mcp = FastMCP("docs-search", instructions="Acme Python SDK documentation: prose search, the v3 OpenAPI spec, "
                                          "and the v2->v3 changelog. Read-only.")

# ---------------------------------------------------------------- search_docs, two versions of the same tool

SEARCH_DOC_V1 = "Search the docs."

SEARCH_DOC_V2 = """Semantic search over the Acme Python SDK prose docs (guides, reference pages, code samples)
for ONE major SDK version. Returns the 3 best chunks, each with a chunk_id you should cite in `sources`.

When to use: how-to and behaviour questions ("how do I upload a file", "how does retry work").
When NOT to use: endpoint schemas (use get_openapi_spec) or "is X deprecated?" (use check_deprecation).

api_version: the MAJOR version the developer's code will run on: "v2" or "v3". Published docs:
  v3 = SDK 3.0-3.2, current. Default to v3 for new code and for migrations.
  v2 = SDK 2.x, deprecated. Use only to read what the developer's existing v2 code does.
There are no docs for any other version. If the developer names one (say v4), do not guess its API and do
not answer from v2 docs: call with "v3", and tell the developer v3 is the latest published version.

On failure the error text says what to do next. Follow it rather than repeating the same call."""


def _major(api_version: str) -> str | None:
    m = re.fullmatch(r"v?(\d+)(?:\.[\dx*]+)*", api_version.strip().lower())
    return f"v{m.group(1)}" if m else None


def _search(query: str, api_version: str) -> dict:
    major = _major(api_version)
    if major not in PUBLISHED:
        if PROMPTS == "v1":
            raise ToolError("Error 3")
        asked = f"{major}.x" if major else repr(api_version)
        raise ToolError(
            f"no docs for {asked}: that version is not published (this is not an outage, the docs index is up). "
            f"Latest published docs are {LATEST} (SDK {PUBLISHED[LATEST]['covers']}); v2 is deprecated. "
            f"Retry: search_docs(query={query!r}, api_version=\"{LATEST}\"). Methods removed or renamed in v3 are "
            f"listed by check_deprecation(symbol, api_version=\"v3\") and on the v3 changelog page "
            f"(search_docs(\"what changed in v3\", \"v3\")). Do not fall back to v2 samples: Client.request() and "
            f"paginate_auto() no longer exist in v3.")
    try:
        # The embedder may print while it loads; stdout is the JSON-RPC channel, so keep it clean.
        with contextlib.redirect_stdout(sys.stderr):
            return w7.search_docs(query, major)
    except Exception as exc:  # index or model failed to load: transient, and it says so
        raise ToolError(f"docs index unavailable ({type(exc).__name__}). This is an outage, not a missing "
                        f"version: retry once, then answer from check_deprecation/get_openapi_spec and say the "
                        f"prose docs could not be searched.") from exc


if PROMPTS == "v1":
    @mcp.tool(name="search_docs", description=SEARCH_DOC_V1)
    def search_docs(query: str, api_version: str) -> dict:
        return _search(query, api_version)
else:
    @mcp.tool(name="search_docs", description=SEARCH_DOC_V2)
    def search_docs(query: str, api_version: str) -> dict:
        return _search(query, api_version)

# ---------------------------------------------------------------- the other two Week 7 tools, unchanged


@mcp.tool(description=w7.TOOLS[1]["description"])
def get_openapi_spec(path: str) -> dict:
    return w7.get_openapi_spec(path)


@mcp.tool(description=w7.TOOLS[2]["description"])
def check_deprecation(symbol: str, api_version: str) -> dict:
    return w7.check_deprecation(symbol, api_version)

# ---------------------------------------------------------------- resource: app-attached, not model-invoked


@mcp.resource("docs://version-support-matrix", name="version-support-matrix", mime_type="application/json",
              description="Which SDK major versions have published docs and their support status.")
def version_support_matrix() -> str:
    return json.dumps({"published_docs": PUBLISHED, "latest": LATEST})


if __name__ == "__main__":
    mcp.run("stdio")
