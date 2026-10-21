"""Week 11: the docs assistant in production. Every request writes one trace with per-span time, tokens and cost.

    .venv/bin/python week11_app.py "how do I upload a file"                  # one request on the live prompt
    .venv/bin/python week11_app.py "how do I upload a file" --prompt v1      # pin a prompt version

Pipeline (three spans, in this order):
  retrieval   dense MiniLM + lexical boost over the SDK corpus (local, no API charge)
  tools       check_deprecation lookups from the Week 7 changelog (local, no API charge)
  generation  one LLM call (week7_tools.call_llm: haiku through the headless claude CLI)

A trace is one JSON object per line in week11/logs/requests-YYYY-MM-DD.jsonl (UTC day of `ts`). It holds
everything the support drill needs: who (user_id, session_id), when (ts), what kind of input (input_type),
which release (prompt_version + prompt_sha), what was retrieved (retrieved_context_ids), what came out
(output + answer_text), and per-span latency_ms / tokens / cost_usd.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import week7_tools
from week11_logq import output_index
from week7_tools import CHANGELOG, LLMError, call_llm, check_deprecation, get_openapi_spec

ROOT = Path(__file__).parent
W11 = ROOT / "week11"
LOG_DIR = W11 / "logs"
PROMPTS = W11 / "prompts"
COLLECTION = "w11_docs"
TRACE_SCHEMA = 2  # 2: + output_index (week11_logq.output_index), written at log time

# A release is a prompt template plus the retrieval settings shipped with it. Bump the version for any change
# to either, so every trace names exactly what produced it.
RELEASES = {
    "v1": {"prompt": "answer_v1.txt", "top_k": 4, "filter_to_target": False, "deprecations_from": "question"},
    # Week 11 incident fix (drill 1, tr-a3d4b7eb86a5 / tr-bc9b9c00ce4a): v3 developers were served archived v2
    # pages and got v2 code. Retrieval is scoped to the developer's version unless the question names both,
    # deprecation lookups cover the retrieved text too, and the prompt forbids deprecated names in code.
    "v2": {"prompt": "answer_v2.txt", "top_k": 4, "filter_to_target": True, "deprecations_from": "question+context"},
    # v2 named the replacement but gave no usage (judge FAIL on W11-02 3/3), so the tools stage now also fetches
    # the OpenAPI entry of each replacement_path a deprecation lookup returns.
    "v3": {"prompt": "answer_v3.txt", "top_k": 4, "filter_to_target": True, "deprecations_from": "question+context",
           "spec_for_replacements": True},
    # v3 left two wording gaps: "not `upload_file`" carries no migration note (E08 3/3), and v2 answers sometimes
    # dropped the "removed in v3" note (W11-03 1/3). Prompt-only change; retrieval and tools are v3's.
    "v4": {"prompt": "answer_v4.txt", "top_k": 4, "filter_to_target": True, "deprecations_from": "question+context",
           "spec_for_replacements": True},
}
LIVE = "v1"  # v4 is the candidate; it ships through the canary in week11/release.md, then flip this line

CHUNK_ID = re.compile(r"^v[23]-[\w-]+::")
SYMBOLS = {e["symbol"]: [e["symbol"], *e["aliases"]] for e in CHANGELOG}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def load_prompt(version: str) -> str:
    return (PROMPTS / RELEASES[version]["prompt"]).read_text()


def input_type(question: str) -> str:
    if "`" in question or re.search(r"\w+\([^)]*=", question):
        return "code_paste"
    if re.search(r"\b\w+Error\b|traceback|not an attribute|is missing|not set|exception", question, re.I):
        return "error_message"
    return "question"


def sdk_target(question: str) -> str:
    """The SDK version the developer is on: v2 only if they say so, otherwise v3 (the current release)."""
    q = question.lower()
    if re.search(r"\bv2\b", q) and not re.search(r"\bv3\b|migrat|rewrite|upgrade", q):
        return "v2"
    return "v3"


def retrieval_scope(question: str) -> str | None:
    """The one version to retrieve from, or None when the question spans both (migration, v2 vs v3)."""
    q = question.lower()
    if re.search(r"\bv2\b", q) and re.search(r"\bv3\b|migrat|rewrite|upgrade", q):
        return None
    return sdk_target(question)


def symbols_in(text: str) -> list[str]:
    found = []
    for symbol, names in SYMBOLS.items():
        if any(re.search(rf"\b{re.escape(n.split('.')[-1])}\b", text, re.I) for n in names):
            found.append(symbol)
    return found


def render_answer(output: dict | None) -> str:
    """The output contract as Week 6 answer text (prose, one fenced block, one chunk citation)."""
    if not output:
        return "I don't know based on the provided documents."
    parts = [output["answer"].strip()]
    code = output["code"].strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
    if code:
        parts.append(f"```python\n{code}\n```")
    cite = next((s for s in output["sources"] if isinstance(s, str) and CHUNK_ID.match(s)), None)
    return "\n\n".join(parts) + (f" [chunk:{cite}]" if cite else "")


def parse_output(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    ok = (isinstance(obj, dict) and isinstance(obj.get("answer"), str) and isinstance(obj.get("code"), str)
          and isinstance(obj.get("sources"), list))
    return obj if ok else None


class DocsAssistant:
    def __init__(self, log_dir: Path | None = LOG_DIR, llm=call_llm) -> None:
        from chunking import load_pages, make_chunks
        from vector_store import SdkVectorStore

        self.log_dir = log_dir
        self.llm = llm
        self.store = SdkVectorStore()
        self.store.ingest(COLLECTION, make_chunks(load_pages(ROOT / "corpus"), "structured"))
        self._search_lock = threading.Lock()  # chroma + the embedder are not thread-safe
        self._write_lock = threading.Lock()
        week7_tools.THINKING_TOKENS = 0

    # ------------------------------------------------------------ spans

    def _retrieve(self, question: str, target: str, release: dict) -> tuple[list, dict]:
        t = time.perf_counter()
        scope = retrieval_scope(question) if release["filter_to_target"] else None
        filters = {"sdk_version": scope} if scope else None
        shadow = []
        with self._search_lock:
            hits = self.store.search(COLLECTION, question, top_k=release["top_k"], filters=filters)
            if filters:  # what the unscoped search would have served instead; never shown to the model
                ids = {h.chunk.chunk_uid for h in hits}
                shadow = [h for h in self.store.search(COLLECTION, question, top_k=release["top_k"])
                          if h.chunk.chunk_uid not in ids]
            tokens = len(self.store.embedder.tokenizer(question)["input_ids"])
        return hits, {"name": "retrieval", "latency_ms": round((time.perf_counter() - t) * 1000, 1),
                      "tokens": {"embed_in": tokens}, "cost_usd": 0.0,
                      "attrs": {"top_k": release["top_k"], "filters": filters, "embedder": "all-MiniLM-L6-v2 (local)",
                                **({"shadow_context_ids": [h.chunk.chunk_uid for h in shadow]} if filters else {})},
                      "_shadow": shadow}

    def _tools(self, question: str, hits: list, target: str, release: dict, shadow: list = ()) -> tuple[list, dict]:
        t = time.perf_counter()
        text = question if release["deprecations_from"] == "question" else \
            question + "\n" + "\n".join(h.chunk.text for h in [*hits, *shadow])
        calls = [{"tool": "check_deprecation", "args": {"symbol": s, "api_version": target},
                  "result": check_deprecation(s, target)} for s in symbols_in(text)]
        if release.get("spec_for_replacements"):
            paths = sorted({c["result"]["replacement_path"] for c in calls if c["result"].get("replacement_path")})
            calls += [{"tool": "get_openapi_spec", "args": {"path": p}, "result": get_openapi_spec(p)} for p in paths]
        return calls, {"name": "tools", "latency_ms": round((time.perf_counter() - t) * 1000, 1),
                       "tokens": {"in": 0, "out": 0}, "cost_usd": 0.0,
                       "attrs": {"calls": [f"{c['tool']}({next(iter(c['args'].values()))})" for c in calls]}}

    def _generate(self, question: str, hits: list, calls: list, target: str, template: str) -> tuple[dict, dict]:
        context = "\n\n".join(f"[{h.chunk.chunk_uid}] (SDK {h.chunk.sdk_version})\n{h.chunk.text}" for h in hits)
        notes = "\n".join(json.dumps(c["result"]) for c in calls if c["tool"] == "check_deprecation") or "(none)"
        spec = "\n".join(json.dumps(c["result"]) for c in calls if c["tool"] == "get_openapi_spec") or "(none)"
        prompt = (template.replace("{question}", question).replace("{context}", context)
                  .replace("{deprecations}", notes).replace("{spec}", spec).replace("{sdk_target}", target))
        t = time.perf_counter()
        try:
            resp = self.llm("You are the Acme SDK documentation assistant. Output only the JSON object requested.",
                            prompt, timeout_s=90)
            error = None
        except (LLMError, TimeoutError) as exc:
            resp, error = {"text": "", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "api_s": 0,
                           "model": week7_tools.MODEL}, str(exc)
        span = {"name": "generation", "latency_ms": round((time.perf_counter() - t) * 1000, 1),
                "tokens": {"in": resp["tokens_in"], "out": resp["tokens_out"]},
                "cost_usd": round(resp["cost_usd"], 7),
                "attrs": {"model": resp["model"], "api_ms": round(resp.get("api_s", 0) * 1000),
                          "prompt_chars": len(prompt), **({"error": error} if error else {})}}
        return {"text": resp["text"], "error": error}, span

    # ------------------------------------------------------------ one request

    def ask(self, question: str, user_id: str = "anon", session_id: str | None = None,
            prompt_version: str = LIVE, ts: str | None = None, extra: dict | None = None) -> dict:
        release = RELEASES[prompt_version]
        template = load_prompt(prompt_version)
        target = sdk_target(question)
        t0 = time.perf_counter()
        hits, s_ret = self._retrieve(question, target, release)
        calls, s_tools = self._tools(question, hits, target, release, s_ret.pop("_shadow"))
        gen, s_gen = self._generate(question, hits, calls, target, template)
        output = parse_output(gen["text"])
        spans = [s_ret, s_tools, s_gen]
        trace = {
            "trace_id": "tr-" + uuid.uuid4().hex[:12],
            "schema": TRACE_SCHEMA,
            "ts": ts or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "user_id": user_id,
            "session_id": session_id or "s-" + uuid.uuid4().hex[:8],
            "input_type": input_type(question),
            "sdk_target": target,
            "prompt_version": prompt_version,
            "prompt_sha": _sha(template),
            "model": s_gen["attrs"]["model"],
            "question": question,
            "retrieved_context_ids": [h.chunk.chunk_uid for h in hits],
            "retrieved": [{"rank": i, "chunk_id": h.chunk.chunk_uid, "sdk_version": h.chunk.sdk_version,
                           "score": round(h.final_score, 4)} for i, h in enumerate(hits, 1)],
            "tool_calls": calls,
            "output": output,
            "answer_text": render_answer(output),
            "status": "ok" if output else ("llm_error" if gen["error"] else "bad_output"),
            "spans": spans,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "tokens": sum(sum(s["tokens"].values()) for s in spans if s["name"] != "retrieval"),
            "cost_usd": round(sum(s["cost_usd"] for s in spans), 7),
            **(extra or {}),
        }
        trace["output_index"] = output_index(trace, {h.chunk.chunk_uid: h.chunk.text for h in hits})
        if self.log_dir:
            self.write(trace)
        return trace

    def write(self, trace: dict) -> Path:
        path = self.log_dir / f"requests-{trace['ts'][:10]}.jsonl"
        with self._write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(trace) + "\n")
        return path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--prompt", default=LIVE, choices=sorted(RELEASES))
    p.add_argument("--user", default="cli")
    p.add_argument("--no-log", action="store_true")
    a = p.parse_args()
    bot = DocsAssistant(log_dir=None if a.no_log else LOG_DIR)
    trace = bot.ask(a.question, user_id=a.user, prompt_version=a.prompt)
    print(trace["answer_text"])
    print(json.dumps({k: trace[k] for k in ("trace_id", "prompt_version", "retrieved_context_ids", "latency_ms",
                                             "tokens", "cost_usd")}, indent=1))
    for s in trace["spans"]:
        print(f"  {s['name']:10} {s['latency_ms']:>8} ms  tokens={s['tokens']}  ${s['cost_usd']}")


if __name__ == "__main__":
    main()
