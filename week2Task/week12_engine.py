"""Week 12: the integrated SDK docs answer engine. One request = one trace id, from question in to answer out.

    intake        redact secrets (before the model, the MCP server or the log sees them), resolve the caller's version
    agent         the Week 7 plan -> act -> observe loop, hosted as in Week 9: every tool comes from tools/list over
                  MCP (week12_server.py), nothing is hardcoded. Each lap is one LLM call (week7_tools.call_llm).
    mcp hop       tools/call carries _meta.trace_id; the server logs its own span under the same id and echoes it
    code_check    week12_guards.check_code: parse + imports + every client method / parameter vs THAT version
    render        answer, code, version notes (deprecations surfaced unasked), citations that name the SDK version

Releases (one code path, flags per release, like Week 11):
  r0  Tuesday's wiring: the Week 9 MCP host + Week 9 docs server and prompt exactly as they were ("you answer with
      v3 code"); the caller's version reaches the model only as words appended to the question.
  r1  the version-aware prompt + the Week 12 server (symbol_exists, sdk_version on every tool). Version still
      enforced by nothing but the prompt.
  r2  r1 + the host ENFORCES the version on every tools/call (metadata filter pinned in code), the emitted code is
      checked against the caller's symbol table with one repair lap (withheld if it still fails), version notes are
      generated from the changelog, and citations not returned by a tool are dropped.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
import uuid
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

import week7_tools
import week12_guards as g
from week7_tools import CONTRACT as W7_CONTRACT, LLMError, call_llm

ROOT = Path(__file__).parent
W12 = ROOT / "week12"
LOG_DIR = W12 / "logs"
RELEASES = {
    "r0": {"config": W12 / "mcp_r0.json", "prompt": "w9", "enforce_version": False, "code_check": False,
           "notices": False, "ground_citations": False},
    "r1": {"config": W12 / "mcp.json", "prompt": "w12", "enforce_version": False, "code_check": False,
           "notices": False, "ground_citations": False},
    "r2": {"config": W12 / "mcp.json", "prompt": "w12", "enforce_version": True, "code_check": True,
           "notices": True, "ground_citations": True},
}
LIVE = "r2"
MAX_ITERS, MAX_COST_USD, MAX_WALL_S, MAX_REPAIRS = 8, 0.06, 150.0, 1

PAGES = {}  # page_id -> (sdk_version, corpus path)
for _p in sorted((ROOT / "corpus").rglob("*.md")):
    _m = re.search(r"^page_id:\s*(\S+)", _p.read_text(), re.M)
    if _m:
        PAGES[_m.group(1)] = (_p.parent.name.removeprefix("sdk_"), str(_p.relative_to(ROOT)))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------- prompts

def system_prompt(release: str, tools: list[dict], resources: list[dict], ver: g.Resolved) -> str:
    listing = json.dumps(tools, indent=1)
    attached = "\n".join(f"[{r['uri']}]\n{r['text']}" for r in resources)
    if RELEASES[release]["prompt"] == "w9":  # Week 9's host prompt, unchanged
        return f"""You are a migration agent for the Acme Python SDK. Developers bring v2 code or v3 questions; you answer with v3 code.
You work in steps. Each reply is exactly ONE JSON object and nothing else:
  {{"thought": "<why>", "tool": "<tool name>", "args": {{...}}}}   to call one tool, or
  {{"thought": "<why>", "final": <output contract>}}                 when you are done.
Tools (discovered over MCP):
{listing}
{"Context attached by the app:" + chr(10) + attached if attached else ""}
Output contract for "final":
{W7_CONTRACT}"""
    target = ver.code_target
    upgrade = ("The caller is UPGRADING from v2: write v3 code, and list every v2 symbol in their code that changed."
               if ver.migration else "")
    assumed = ("No version was given, so the host assumed the current release; say \"assuming SDK 3.0\" in the answer."
               if ver.source == "default" else "")
    unsupported = (f"The caller named SDK {ver.unsupported}, which has no published docs. Say so plainly and answer "
                   f"for the latest published version." if ver.unsupported else "")
    return f"""You are the Acme Python SDK docs answer engine. SDK v2.x and v3.x are BOTH live and supported; about 40% of integrators are on v2.
The host resolved the caller's version BEFORE you saw the question:
  caller is on SDK {ver.minor} (docs: {ver.major}), resolved from: {ver.evidence}.
  Code you write must run on SDK {target}. Pass sdk_version="{ver.minor if target == ver.major else '3.0'}" to tools.
{upgrade} {assumed} {unsupported}
Rules:
- Answer for SDK {target} only. Put a method, import or parameter in code only if a tool result for {target} shows it. If unsure, call symbol_exists first. Never invent a signature.
- If the question asks about a method or option that does not exist in SDK {target}, say so plainly in the first sentence (e.g. "`client.request()` no longer exists in 3.0") and give the replacement the changelog names.
- Call check_deprecation on every v2 symbol your answer uses or the question mentions, and list each one that was removed, renamed or changed in "deprecations" even if nobody asked.
- If the {target} docs do not cover the question, say "The {target} docs don't cover this" and leave code empty. Never substitute code from the other version.
- sources: chunk_ids exactly as tool results returned them.
You work in steps. Each reply is exactly ONE JSON object and nothing else:
  {{"thought": "<why>", "tool": "<tool name>", "args": {{...}}}}   to call one tool, or
  {{"thought": "<why>", "final": <output contract>}}                 when you are done.
Tools (discovered over MCP):
{listing}
{"Context attached by the app:" + chr(10) + attached if attached else ""}
Output contract for "final" (ONE JSON object, exactly these keys):
{{"answer": "<1-3 sentences for the developer>",
 "code": "<runnable Python for SDK {target}, newlines as \\n, or empty string>",
 "deprecations": [{{"symbol": "<name>", "replacement": "<replacement>", "changed_in": "<version>"}}],
 "sources": ["<chunk_id from a tool result>"]}}"""


def render_steps(question: str, steps: list[dict]) -> str:
    lines = [f"QUESTION:\n{question}\n"]
    for s in steps:
        lines.append(f"YOU:\n{s['reply']}\n{s.get('label', 'TOOL RESULT')}:\n{json.dumps(s['result'])[:3000]}\n")
    lines.append("Reply with the next JSON object.")
    return "\n".join(lines)


def parse_action(text: str) -> dict | None:
    start = text.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def normalise_final(final) -> dict | None:
    """Both contracts (Week 7's v3_code and Week 12's code) -> one shape."""
    if not isinstance(final, dict) or not isinstance(final.get("answer"), str):
        return None
    code = final.get("code", final.get("v3_code"))
    if not isinstance(code, str) or not isinstance(final.get("sources", []), list):
        return None
    deps = [d for d in final.get("deprecations") or [] if isinstance(d, dict)]
    return {"answer": final["answer"].strip(), "code": g.strip_fence(code).strip(), "deprecations": deps,
            "sources": [str(s) for s in final.get("sources") or []]}


# ---------------------------------------------------------------- version notes and citations (deterministic)

def _symbol_patterns(entry: dict) -> list[str]:
    names = {a.split(".")[-1] for a in [entry["symbol"], *entry["aliases"]]}
    # "request" is also an English word: only the call form counts
    return [rf"(?:[Cc]lient\.|\.){re.escape(n)}\b" if n == "request" else rf"\b{re.escape(n)}\b" for n in names]


def version_notes(ver: g.Resolved, question: str, out: dict | None) -> list[dict]:
    text = "\n".join([question, (out or {}).get("code", ""), (out or {}).get("answer", "")])
    listed = " ".join(str(d.get("symbol", "")) for d in (out or {}).get("deprecations", []))
    notes = []
    if ver.unsupported:
        notes.append({"kind": "unsupported_version", "text": f"There are no docs for SDK {ver.unsupported}. The "
                      f"latest published version is {g.PUBLISHED[g.LATEST]['covers']}; this answer is for 3.0."})
    if ver.source == "default":
        notes.append({"kind": "assumed_version", "text": "No SDK version was given, so this answer is for 3.0 (the "
                      "current release). If you are on 2.x, ask again with your version: v2 and v3 differ."})
    for e in g.CHANGELOG + g.DOCS_ONLY_RENAMES:
        if not any(re.search(p, text) for p in _symbol_patterns(e)) and e["symbol"].split(".")[-1] not in listed:
            continue
        sym = e["symbol"] + ("()" if e["symbol"][0].islower() or "." in e["symbol"] else "")
        if ver.code_target == "v2":
            line = (f"`{sym}` works on {ver.minor}, but was {e['kind']} in {e['changed_in']}. When you upgrade, use "
                    f"{e['replacement']}.")
        elif e["status"] == "default_changed":
            line = f"The default changed in {e['changed_in']}: {e['note']} {e['replacement'].capitalize()}."
        else:
            line = f"`{sym}` no longer exists in {e['changed_in']} ({e['kind']}). Use {e['replacement']}."
        notes.append({"kind": "deprecation", "symbol": e["symbol"], "changed_in": e["changed_in"], "text": line,
                      "source": e["source"]})
    return notes


def citation(source: str, evidence: dict[str, dict]) -> dict:
    """A source id -> {id, sdk_version, link, grounded}. Grounded = some tool returned it in THIS trace."""
    if source in evidence:
        return {"id": source, **evidence[source], "grounded": True}
    page_id = source.split("::")[0]
    if page_id in PAGES:
        v, path = PAGES[page_id]
        anchor = source.split("::")[1] if "::" in source else ""
        return {"id": source, "sdk_version": v, "url": f"{path}#{anchor}" if anchor else path, "grounded": False}
    if source.lstrip("openapi:").startswith("/v3/"):
        return {"id": source, "sdk_version": "v3", "url": "week7/openapi_v3.json", "grounded": False}
    return {"id": source, "sdk_version": None, "url": None, "grounded": False}


def render(ver: g.Resolved, out: dict | None, notes: list[dict], cites: list[dict], check: dict | None,
           withheld: str | None) -> str:
    if out is None:
        return "I don't know based on the provided documents."
    parts = [out["answer"]]
    if out["code"]:
        parts.append(f"```python\n{out['code']}\n```")
    if withheld:
        parts.append(withheld)
    if notes:
        parts.append(f"Version notes (SDK {ver.minor}):\n" + "\n".join(f"- {n['text']}" for n in notes))
    if cites:
        parts.append("Sources:\n" + "\n".join(
            f"- [SDK {c['sdk_version'] or '?'}{' ' + g.PUBLISHED[c['sdk_version']]['covers'] if c['sdk_version'] in g.PUBLISHED else ''}] "
            f"[{c['id']}]({c['url'] or '#'}){'' if c['grounded'] else ' (not returned by any tool in this request)'}"
            for c in cites))
    if check and check["status"] != "n/a":
        parts.append(f"Code checked against the SDK {check['version']} symbol table: {check['status']} "
                     f"({check['checked']} symbols).")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- the engine (an MCP host)

class Engine:
    """Connect once (initialize -> tools/list -> resources/read), then answer any number of questions."""

    def __init__(self, release: str = LIVE, llm=call_llm, log_dir: Path | None = LOG_DIR, label: str = "adhoc",
                 config: Path | None = None) -> None:
        self.release, self.flags, self.llm, self.log_dir, self.label = release, RELEASES[release], llm, log_dir, label
        self.config = config or self.flags["config"]
        self.tools: dict[str, dict] = {}
        self.sessions: dict[str, ClientSession] = {}
        self.resources: list[dict] = []
        self.discovery: dict = {}
        self._stack = AsyncExitStack()
        self._write = asyncio.Lock()
        week7_tools.THINKING_TOKENS = 0  # Week 7's headline setting

    async def __aenter__(self) -> "Engine":
        t0 = time.perf_counter()
        servers = json.loads(Path(self.config).read_text())["mcpServers"]
        for server, spec in servers.items():
            params = StdioServerParameters(command=spec["command"], args=spec.get("args", []),
                                           env={**get_default_environment(), **spec.get("env", {})},
                                           cwd=str(ROOT / spec.get("cwd", ".")))
            read, write = await self._stack.enter_async_context(stdio_client(params, errlog=open(os.devnull, "w")))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            init = await session.initialize()
            self.sessions[server] = session
            for tool in (await session.list_tools()).tools:
                exposed = tool.name if tool.name not in self.tools else f"{server}.{tool.name}"
                self.tools[exposed] = {"server": server, "name": tool.name, "description": tool.description or "",
                                       "schema": tool.inputSchema}
            if init.capabilities.resources:
                for res in (await session.list_resources()).resources:
                    contents = (await session.read_resource(res.uri)).contents
                    self.resources.append({"server": server, "uri": str(res.uri),
                                           "text": "".join(getattr(c, "text", "") for c in contents)})
        self.discovery = {"servers": list(servers), "tools": {n: t["server"] for n, t in self.tools.items()},
                          "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    def tool_listing(self) -> list[dict]:
        return [{"name": n, "description": t["description"], "input_schema": t["schema"]} for n, t in self.tools.items()]

    async def call_tool(self, name: str, args: dict, ver: g.Resolved, trace_id: str, span_no: int) -> dict:
        t0 = time.perf_counter()
        if name not in self.tools:
            return {"tool": name, "args": args, "isError": True, "latency_ms": 0.0,
                    "result": f"unknown tool {name!r}; tools are {sorted(self.tools)}"}
        tool = self.tools[name]
        sent = dict(args) if isinstance(args, dict) else {}
        enforced = None
        if self.flags["enforce_version"] and "sdk_version" in tool["schema"].get("properties", {}):
            raw = str(sent.get("sdk_version") or "").strip()
            asked = g._major_minor(raw if raw.lower().startswith("v") else f"v{raw}") if raw else None
            if not asked or asked[0] not in ver.allowed:
                # the metadata filter is pinned in code: the caller's version, or 3.0 for an upgrade's new code
                pinned = "3.0" if ver.migration else ver.minor
                enforced = {"from": sent.get("sdk_version"), "to": pinned}
                sent["sdk_version"] = pinned
        res = await self.sessions[tool["server"]].call_tool(tool["name"], sent,
                                                            meta={"trace_id": trace_id, "parent_span": f"s{span_no}"})
        text = "".join(getattr(c, "text", "") for c in res.content)
        try:
            content = json.loads(text)
        except json.JSONDecodeError:
            content = text
        server = content.pop("_trace", None) if isinstance(content, dict) else None
        return {"tool": name, "server": tool["server"], "args": args, "args_sent": sent, "enforced": enforced,
                "isError": bool(res.isError), "result": content, "server_span": server,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}

    async def ask(self, question: str, sdk_version: str | None = None, case_id: str | None = None) -> dict:
        trace_id = "tr-" + uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        spans: list[dict] = []

        def span(name: str, started: float, **kw) -> dict:
            s = {"span_id": f"s{len(spans) + 1}", "name": name, "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                 "cost_usd": 0.0, **kw}
            spans.append(s)
            return s

        # ---- intake: redact, then resolve the version (before any retrieval)
        ts = time.perf_counter()
        clean, kinds = g.redact(question)
        ver = g.resolve_version(clean, sdk_version)
        span("intake", ts, attrs={"redactions": kinds, "version": ver.as_dict()})
        user_q = clean
        if self.flags["prompt"] == "w9" and sdk_version:
            user_q = f"{clean}\n(I'm on SDK {sdk_version}.)"  # Tuesday: the version was only words in the question
        system = system_prompt(self.release, self.tool_listing(), self.resources, ver)

        steps: list[dict] = []
        calls: list[dict] = []
        laps, cost, tokens = 0, 0.0, 0
        status, out, repairs, check, withheld = "budget_exceeded", None, 0, None, None
        while laps < MAX_ITERS:
            if time.perf_counter() - t0 > MAX_WALL_S or cost > MAX_COST_USD:
                break
            ts = time.perf_counter()
            try:
                resp = await asyncio.to_thread(self.llm, system, render_steps(user_q, steps),
                                               max(MAX_WALL_S - (time.perf_counter() - t0), 5))
            except (LLMError, TimeoutError) as exc:
                span("agent.lap", ts, lap=laps + 1, error=str(exc)[:200])
                status = "llm_error"
                break
            laps += 1
            cost += resp["cost_usd"]
            tokens += resp["tokens"]
            action = parse_action(resp["text"]) or {}
            if "tool" not in action and "final" not in action and normalise_final(action):
                action = {"thought": "(bare output contract, accepted as final)", "final": action}
            span("agent.lap", ts, lap=laps, cost_usd=round(resp["cost_usd"], 7),
                 tokens={"in": resp["tokens_in"], "out": resp["tokens_out"]}, model=resp["model"],
                 action=("final" if "final" in action else action.get("tool") or "unparsed"),
                 thought=str(action.get("thought", ""))[:240])
            if "final" in action:
                out = normalise_final(action["final"])
                if out is None:
                    status = "bad_final"
                    break
                status = "done"
                if self.flags["code_check"]:
                    ts = time.perf_counter()
                    check = g.check_code(out["code"], ver.code_target)
                    span("code_check", ts, attrs={"version": ver.code_target, "status": check["status"],
                                                  "violations": check["violations"], "repair": repairs})
                    if check["status"] == "fail" and repairs < MAX_REPAIRS:
                        repairs += 1
                        steps.append({"reply": resp["text"].strip(), "label": "HOST CODE CHECK", "result": {
                            "status": "FAILED", "sdk_version": ver.code_target, "violations": check["violations"],
                            "instruction": f"Your code does not run on SDK {ver.minor if ver.code_target == ver.major else '3.0'}. "
                                           f"Rewrite it using only symbols a tool result for {ver.code_target} shows "
                                           f"(symbol_exists / search_docs with that sdk_version), or return empty code "
                                           f"and say plainly that it does not exist in that version."}})
                        continue
                    if check["status"] == "fail":
                        withheld = (f"(A code sample was withheld: it failed the SDK {ver.code_target} symbol check: "
                                    f"{'; '.join(check['violations'][:2])}.)")
                        out = {**out, "code": ""}
                break
            if action.get("tool"):
                call = await self.call_tool(action["tool"], action.get("args") or {}, ver, trace_id, len(spans) + 1)
                spans.append({"span_id": f"s{len(spans) + 1}", "name": f"mcp.tools/call {action['tool']}",
                              "latency_ms": call["latency_ms"], "cost_usd": 0.0, "server": call.get("server"),
                              "server_span": call.get("server_span"), "enforced": call.get("enforced"),
                              "isError": call["isError"]})
                calls.append(call)
                steps.append({"reply": resp["text"].strip(), "result": call["result"] if not call["isError"]
                              else {"isError": True, "content": call["result"]}})
            else:
                steps.append({"reply": resp["text"].strip(),
                              "result": {"isError": True, "content": "reply was not one JSON object with 'tool' or 'final'"}})

        # ---- render: notes, citations, answer text
        ts = time.perf_counter()
        if check is None and out is not None:  # r0/r1 never act on it, but the trace records what they shipped
            check = {**g.check_code(out["code"], ver.code_target), "observed_only": True}
        evidence = {}
        for c in calls:
            res = c["result"] if isinstance(c["result"], dict) else {}
            for r in res.get("results", []) or []:
                if "chunk_id" in r:
                    v = r.get("sdk_version") or r["chunk_id"].split("-")[0]
                    evidence[r["chunk_id"]] = {"sdk_version": v, "url": r.get("url") or citation(r["chunk_id"], {})["url"]}
            if res.get("source"):
                evidence[res["source"]] = {"sdk_version": res["source"].split("-")[0],
                                           "url": citation(res["source"], {})["url"]}
            if res.get("path", "").startswith("/v3/"):
                evidence[res["path"]] = {"sdk_version": "v3", "url": f"week7/openapi_v3.json#{res['path']}"}
        cites = [citation(s, evidence) for s in (out or {}).get("sources", [])]
        dropped = []
        if self.flags["ground_citations"]:
            dropped = [c["id"] for c in cites if not c["grounded"]]
            cites = [c for c in cites if c["grounded"]]
        notes = version_notes(ver, clean, out) if self.flags["notices"] else []
        answer_text = render(ver, out, notes, cites, check if self.flags["code_check"] else None, withheld)
        span("render", ts, attrs={"notes": len(notes), "citations": len(cites), "dropped_citations": dropped})

        server_ids = [s["server_span"]["trace_id"] for s in spans if s.get("server_span")]
        trace = {
            "trace_id": trace_id, "ts": now(), "release": self.release, "run_label": self.label, "case_id": case_id,
            "question": clean, "redactions": kinds, "sdk_version_flag": sdk_version, "version": ver.as_dict(),
            "tools_discovered": self.discovery.get("tools"), "tool_calls": calls, "output": out, "code_check": check,
            "notes": notes, "citations": cites, "dropped_citations": dropped, "withheld": withheld,
            "repairs": repairs, "answer_text": answer_text, "status": status, "llm_calls": laps,
            "tokens": tokens, "cost_usd": round(cost, 7), "spans": spans,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "trace_propagation": {"mcp_calls": len(calls), "server_spans": len(server_ids),
                                  "all_match": bool(server_ids) and all(i == trace_id for i in server_ids)},
        }
        trace = g.redact_obj(trace)
        if self.log_dir:
            await self.write(trace)
        return trace

    async def write(self, trace: dict) -> Path:
        path = self.log_dir / f"requests-{trace['ts'][:10]}.jsonl"
        async with self._write:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(g.redact_obj(trace)) + "\n")
        return path


def print_trace(trace: dict) -> None:
    print(trace["answer_text"])
    v = trace["version"]
    print(f"\n--- trace {trace['trace_id']}  release {trace['release']}  status {trace['status']}")
    print(f"    version: SDK {v['minor']} -> docs {v['major']}, code must run on {v['code_target']} "
          f"(resolved from {v['source']}: {v['evidence']})")
    if trace["redactions"]:
        print(f"    redacted at intake: {trace['redactions']}")
    for s in trace["spans"]:
        extra = ""
        if s.get("server_span"):
            ss = s["server_span"]
            extra = f"  server span {ss['span']} {ss['latency_ms']} ms  trace_id={ss['trace_id']}"
        if s.get("enforced"):
            extra += f"  ENFORCED sdk_version {s['enforced']['from']!r} -> {s['enforced']['to']!r}"
        if s.get("tokens"):
            extra += f"  tokens={s['tokens']} action={s.get('action')}"
        print(f"    {s['span_id']:>4} {s['name']:34} {s['latency_ms']:>9.1f} ms  ${s['cost_usd']:.6f}{extra}")
    tp = trace["trace_propagation"]
    print(f"    total {trace['latency_ms']:.0f} ms  ${trace['cost_usd']:.6f}  {trace['llm_calls']} LLM calls  "
          f"{trace['tokens']} tokens  |  trace id survived the MCP hop: {tp['all_match']} "
          f"({tp['server_spans']}/{tp['mcp_calls']} server spans carry {trace['trace_id']})")


async def ask_once(question: str, sdk_version: str | None, release: str, log: bool = True) -> dict:
    async with Engine(release, log_dir=LOG_DIR if log else None, label="cli") as eng:
        return await eng.ask(question, sdk_version)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--sdk-version", help="the caller's installed SDK version, e.g. 2.4 (the IDE plugin sends this)")
    p.add_argument("--release", default=LIVE, choices=sorted(RELEASES))
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    trace = asyncio.run(ask_once(a.question, a.sdk_version, a.release))
    print(json.dumps(trace, indent=1) if a.json else "", end="")
    if not a.json:
        print_trace(trace)


if __name__ == "__main__":
    main()
