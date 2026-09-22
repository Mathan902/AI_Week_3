"""Week 7: the docs agent's tools, the shared LLM call, and the output contract.

Both the agent (week7_agent.py) and the fixed workflow (week7_workflow.py) import everything from
here, so they run the same tools, the same model and the same output contract.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent
W7 = ROOT / "week7"
MODEL = "haiku"  # claude-haiku-4-5 through the headless claude CLI; the same model for both systems
SPEC = json.loads((W7 / "openapi_v3.json").read_text())
CHANGELOG = json.loads((W7 / "changelog_v3.json").read_text())
API_VERSIONS = ["v2", "v3"]
THINKING_TOKENS: int | None = None  # None = the CLI default (extended thinking on); 0 = off. Same for both systems.

# ---------------------------------------------------------------- tool descriptions

# Before Week 7: the loop had two tools whose descriptions overlap. Both claim "endpoints" and
# "parameters", so the model cannot tell which one answers "what does /v3/invoices take?".
TOOLS_V1 = [
    {"name": "search_docs",
     "description": "Search the Acme SDK documentation for anything about endpoints, parameters, methods, "
                    "errors or changes between versions.",
     "parameters": {"query": {"type": "string"}, "api_version": {"type": "string"}}},
    {"name": "get_openapi_spec",
     "description": "Get API information about an endpoint, including its parameters and how to call it.",
     "parameters": {"path": {"type": "string"}}},
]

# Week 7: each description names exactly one job and says what it does NOT do; api_version is an enum.
TOOLS = [
    {"name": "search_docs",
     "description": "Semantic search over the prose SDK documentation pages (guides, reference text, code "
                    "samples) of ONE SDK version. Use it for how-to and behaviour questions. It does not return "
                    "endpoint schemas and does not say whether a symbol is deprecated.",
     "parameters": {"query": {"type": "string", "description": "a natural-language question"},
                    "api_version": {"type": "string", "enum": API_VERSIONS}}},
    {"name": "get_openapi_spec",
     "description": "Return the OpenAPI operations for ONE exact endpoint path in the v3 API (HTTP method, "
                    "parameters, request body and the SDK call). Takes a path such as /v3/invoices, not a "
                    "question. It does not search prose docs and does not know about v2 or deprecations.",
     "parameters": {"path": {"type": "string", "description": "exact path, e.g. /v3/invoices"}}},
    {"name": "check_deprecation",
     "description": "Look up ONE SDK symbol (method, exception, parameter) in the v3 changelog and migration "
                    "notes. It returns whether the symbol is removed, renamed or had its default changed when your "
                    "code runs on api_version, plus the replacement. It does not search docs or return schemas. "
                    "A symbol the changelog doesn't mention returns status 'not_in_changelog'.",
     "parameters": {"symbol": {"type": "string", "description": "one symbol, e.g. paginate_auto"},
                    "api_version": {"type": "string", "enum": API_VERSIONS,
                                    "description": "the SDK version the caller's code will run on"}}},
]

# ---------------------------------------------------------------- tool implementations

_store = None


def warm_up() -> None:
    """Load the embedder and index before anything is timed, so neither system pays for it."""
    _vector_store()


def _vector_store():
    global _store
    if _store is None:
        from chunking import make_chunks, load_pages
        from vector_store import SdkVectorStore
        _store = SdkVectorStore()
        _store.ingest("w7_docs", make_chunks(load_pages(ROOT / "corpus"), "structured"))
    return _store


def search_docs(query: str, api_version: str) -> dict:
    if api_version not in API_VERSIONS:
        return {"error": f"api_version must be one of {API_VERSIONS}"}
    hits = _vector_store().search("w7_docs", query, top_k=3, filters={"sdk_version": api_version})
    return {"results": [{"chunk_id": h.chunk.chunk_uid, "text": h.chunk.text} for h in hits]}


def get_openapi_spec(path: str) -> dict:
    path = path.strip().rstrip("/")
    if path not in SPEC["paths"]:
        return {"error": f"{path} is not a path in the v3 API", "v3_paths": sorted(SPEC["paths"])}
    return {"path": path, "operations": SPEC["paths"][path]}


def _norm(symbol: str) -> str:
    return re.sub(r"\(\)$", "", symbol.strip().strip("`")).lower()


def check_deprecation(symbol: str, api_version: str) -> dict:
    if api_version not in API_VERSIONS:
        return {"error": f"api_version must be one of {API_VERSIONS}"}
    key = _norm(symbol)
    for entry in CHANGELOG:
        names = {_norm(entry["symbol"]), *(_norm(a) for a in entry["aliases"])}
        if key in names or key.split(".")[-1] in names:
            if api_version == "v2":
                return {"symbol": entry["symbol"], "api_version": "v2", "status": "current_in_v2"}
            return {k: entry[k] for k in ("symbol", "status", "replacement", "replacement_path", "note", "source")}
    return {"symbol": symbol, "api_version": api_version, "status": "not_in_changelog"}


TOOL_FUNCS = {"search_docs": search_docs, "get_openapi_spec": get_openapi_spec, "check_deprecation": check_deprecation}


def run_tool(name: str, args: dict) -> dict:
    if name not in TOOL_FUNCS:
        return {"error": f"unknown tool {name!r}; tools are {sorted(TOOL_FUNCS)}"}
    try:
        return TOOL_FUNCS[name](**args)
    except TypeError as exc:
        return {"error": f"bad arguments for {name}: {exc}"}


# ---------------------------------------------------------------- output contract (both systems)

CONTRACT = """Return ONE JSON object with exactly these keys:
{"answer": "<1-3 sentences for the developer>",
 "v3_code": "<runnable Python for SDK v3, newlines as \\n>",
 "deprecations": [{"symbol": "<v2 symbol the question uses that changed in v3>", "replacement": "<v3 replacement>"}],
 "sources": ["<chunk_id, spec path or changelog source you relied on>"]}
Use an empty list for deprecations when nothing in the question changed between v2 and v3.
Only use SDK calls that appear in tool results."""


def parse_contract(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    ok = (isinstance(obj, dict) and isinstance(obj.get("answer"), str) and isinstance(obj.get("v3_code"), str)
          and isinstance(obj.get("deprecations"), list) and isinstance(obj.get("sources"), list))
    return obj if ok else None


def grade(question: dict, output: dict | None) -> tuple[bool, list[str]]:
    """Deterministic pass/fail for one question, the same for both systems."""
    if output is None:
        return False, ["no valid output contract"]
    code = output["v3_code"].strip().removeprefix("```python").removeprefix("```").removesuffix("```")
    fails = []
    try:
        ast.parse(code)
    except SyntaxError as exc:
        fails.append(f"v3_code does not parse: {exc.msg}")
    fails += [f"v3_code missing /{p}/" for p in question["code_must"] if not re.search(p, code)]
    fails += [f"v3_code still uses /{p}/" for p in question["code_must_not"] if re.search(p, code)]
    listed = " ".join(str(d.get("symbol", "")) for d in output["deprecations"] if isinstance(d, dict)).lower()
    fails += [f"deprecations missing {s}" for s in question["must_flag"] if s.lower() not in listed]
    return not fails, fails


# ---------------------------------------------------------------- the one LLM call both systems use

class LLMError(RuntimeError):
    pass


def call_llm(system: str, prompt: str, timeout_s: float = 120) -> dict:
    """One model call through the headless claude CLI. Returns text plus every token it was billed for."""
    cmd = ["claude", "-p", "--model", MODEL, "--output-format", "json", "--tools", "",
           "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config",
           "--setting-sources", "", "--system-prompt", system]
    start = time.perf_counter()
    try:
        env = {**os.environ, **({"MAX_THINKING_TOKENS": str(THINKING_TOKENS)} if THINKING_TOKENS is not None else {})}
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              cwd=tempfile.gettempdir(), timeout=max(timeout_s, 1), env=env)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"LLM call exceeded {timeout_s:.1f}s") from exc
    latency = time.perf_counter() - start
    try:
        env = json.loads(proc.stdout)
        usage = env["usage"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise LLMError(f"bad CLI output: {proc.stdout[:200]} {proc.stderr[:200]}") from exc
    tokens_in = (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                 + usage.get("cache_read_input_tokens", 0))
    return {"text": env.get("result", ""), "tokens_in": tokens_in, "tokens_out": usage.get("output_tokens", 0),
            "tokens": tokens_in + usage.get("output_tokens", 0), "cost_usd": env.get("total_cost_usd", 0.0),
            "latency_s": latency, "api_s": env.get("duration_api_ms", 0) / 1000, "model": next(iter(env.get("modelUsage", {})), MODEL)}
