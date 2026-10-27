"""Week 9: the docs agent as an MCP HOST. It knows no tool by name; every tool comes from tools/list.

    .venv/bin/python week9_agent.py "How do I migrate client.request(...) to v3?"
    .venv/bin/python week9_agent.py --qid Q01
    .venv/bin/python week9_agent.py --config week9/mcp_config.gateway.json "..."
    .venv/bin/python week9_agent.py --list-tools        # connect, discover, print the catalogue, exit

The servers it connects to live in an MCP config file ({"mcpServers": {name: {command, args, env}}}). Adding
a server is a config edit; this module does not change. For each server the host runs initialize ->
tools/list (-> resources/list + resources/read if the server offers resources), then the plan -> act ->
observe loop of Week 7 with tools/call in place of a local function call.

The model call happens HERE, in the host (call_llm -> the claude CLI). The MCP servers never see the model;
they only receive tools/call with the arguments the model chose.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

from week7_agent import Budgets
from week7_tools import CONTRACT, W7, LLMError, call_llm, parse_contract

ROOT = Path(__file__).parent
W9 = ROOT / "week9"
DEFAULT_CONFIG = W9 / "mcp_config.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Catalogue:
    """Everything discovered from the servers: routable tools and app-attached resources."""
    tools: dict[str, dict] = field(default_factory=dict)          # exposed name -> {server, name, description, schema}
    sessions: dict[str, ClientSession] = field(default_factory=dict)
    resources: list[dict] = field(default_factory=list)            # {server, uri, text}
    servers: dict[str, dict] = field(default_factory=dict)         # server -> serverInfo + tool names


async def connect(config_path: Path, stack: AsyncExitStack) -> Catalogue:
    config = json.loads(config_path.read_text())["mcpServers"]
    cat = Catalogue()
    for server, spec in config.items():
        # A server gets PATH/HOME/USER-style defaults plus only the env its config entry lists, never the
        # host's own environment (API keys included).
        params = StdioServerParameters(command=spec["command"], args=spec.get("args", []),
                                       env={**get_default_environment(), **spec.get("env", {})},
                                       cwd=str(ROOT / spec.get("cwd", ".")))
        read, write = await stack.enter_async_context(stdio_client(params, errlog=open(os.devnull, "w")))
        session = await stack.enter_async_context(ClientSession(read, write))
        init = await session.initialize()
        cat.sessions[server] = session
        listed = (await session.list_tools()).tools
        for tool in listed:
            # Two servers may expose the same name; the second one is prefixed with its server.
            exposed = tool.name if tool.name not in cat.tools else f"{server}.{tool.name}"
            cat.tools[exposed] = {"server": server, "name": tool.name, "description": tool.description or "",
                                  "schema": tool.inputSchema}
        if init.capabilities.resources:
            for res in (await session.list_resources()).resources:
                contents = (await session.read_resource(res.uri)).contents
                cat.resources.append({"server": server, "uri": str(res.uri),
                                      "text": "".join(getattr(c, "text", "") for c in contents)})
        cat.servers[server] = {"serverInfo": init.serverInfo.model_dump(), "protocolVersion": init.protocolVersion,
                               "tools": [t.name for t in listed]}
    return cat


def system_prompt(cat: Catalogue) -> str:
    tools = [{"name": n, "description": t["description"], "input_schema": t["schema"]} for n, t in cat.tools.items()]
    context = "\n".join(f"[{r['server']} resource {r['uri']}]\n{r['text']}" for r in cat.resources)
    return f"""You are a migration agent for the Acme Python SDK. Developers bring v2 code or v3 questions; you answer with v3 code.
You work in steps. Each reply is exactly ONE JSON object and nothing else:
  {{"thought": "<why>", "tool": "<tool name>", "args": {{...}}}}   to call one tool, or
  {{"thought": "<why>", "final": <output contract>}}                 when you are done.
Tools (discovered over MCP):
{json.dumps(tools, indent=1)}
{"Context attached by the app:" + chr(10) + context if context else ""}
Output contract for "final":
{CONTRACT}"""


def render(question: str, steps: list[dict]) -> str:
    lines = [f"QUESTION:\n{question}\n"]
    for s in steps:
        lines.append(f"YOU:\n{s['reply']}\nTOOL RESULT:\n{json.dumps(s['result'])[:3000]}\n")
    lines.append("Reply with the next JSON object.")
    return "\n".join(lines)


def parse_action(text: str) -> dict | None:
    """The FIRST JSON object in the reply. A model that emits two tool calls in one reply gets the first run."""
    start = text.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


async def call_tool(cat: Catalogue, name: str, args: dict) -> dict:
    """One tools/call over MCP. The result goes back to the model as text, error flag included."""
    if name not in cat.tools:
        return {"isError": True, "content": f"unknown tool {name!r}; tools are {sorted(cat.tools)}"}
    tool = cat.tools[name]
    res = await cat.sessions[tool["server"]].call_tool(tool["name"], args if isinstance(args, dict) else {})
    text = "".join(getattr(c, "text", "") for c in res.content)
    try:
        content = json.loads(text)
    except json.JSONDecodeError:
        content = text
    return {"isError": bool(res.isError), "content": content}


async def run_agent(question: str, config_path: Path = DEFAULT_CONFIG, budgets: Budgets = Budgets(), llm=call_llm,
                    log_path: Path | None = None, echo: bool = True) -> dict:
    t0 = time.perf_counter()
    log: list[dict] = []
    totals = {"llm_calls": 0, "tokens": 0, "cost_usd": 0.0}

    def emit(event: dict) -> None:
        event = {"t": round(time.perf_counter() - t0, 2), **event}
        log.append(event)
        if echo:
            print(json.dumps(event))

    async with AsyncExitStack() as stack:
        cat = await connect(config_path, stack)
        emit({"event": "start", "question": question, "config": str(config_path.relative_to(ROOT)),
              "config_sha256": sha256(config_path), "agent_module_sha256": sha256(Path(__file__)),
              "budgets": budgets.__dict__})
        emit({"event": "discovered", "servers": cat.servers, "tool_count": len(cat.tools),
              "tools": {n: t["server"] for n, t in cat.tools.items()},
              "resources": [r["uri"] for r in cat.resources]})
        system = system_prompt(cat)
        steps: list[dict] = []

        def finish(status: str, output: dict | None = None, **extra) -> dict:
            result = {"system": "mcp-agent", "status": status, "output": output, "laps": totals["llm_calls"],
                      "latency_s": round(time.perf_counter() - t0, 2), **totals, **extra}
            emit({"event": "end", **{k: v for k, v in result.items() if k != "output"}})
            if log_path:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text("\n".join(json.dumps(e) for e in log + [{"event": "output", "output": output}]) + "\n")
            return result

        for lap in range(1, budgets.max_iters + 1):
            prompt = render(question, steps)
            elapsed = time.perf_counter() - t0
            if elapsed >= budgets.max_wall_s:
                return finish("budget_exceeded", budget="max_wall_s")
            if totals["tokens"] > budgets.max_tokens:
                return finish("budget_exceeded", budget="max_tokens")
            if totals["cost_usd"] > budgets.max_cost_usd:
                return finish("budget_exceeded", budget="max_cost_usd")
            try:
                # THE model call. It is made by the host; no MCP server is involved in it.
                resp = await asyncio.to_thread(llm, system, prompt, budgets.max_wall_s - elapsed)
            except TimeoutError:
                return finish("budget_exceeded", budget="max_wall_s")
            except LLMError as exc:
                return finish("error", detail=str(exc))
            totals["llm_calls"] += 1
            totals["tokens"] += resp["tokens"]
            totals["cost_usd"] += resp["cost_usd"]
            action = parse_action(resp["text"]) or {}
            if "tool" not in action and "final" not in action and parse_contract(json.dumps(action)):
                action = {"thought": "(bare output contract, accepted as final)", "final": action}
            emit({"event": "lap", "lap": lap, "tokens_lap": resp["tokens"], "cost_total": round(totals["cost_usd"], 5),
                  "thought": str(action.get("thought", ""))[:300], "tool": action.get("tool"),
                  "server": cat.tools.get(action.get("tool") or "", {}).get("server"), "args": action.get("args"),
                  "final": "final" in action,
                  **({} if action.get("tool") or "final" in action else {"unparsed_reply": resp["text"][:400]})})
            if "final" in action:
                output = parse_contract(json.dumps(action["final"])) if isinstance(action["final"], dict) else None
                return finish("done" if output else "bad_final", output)
            if action.get("tool"):
                result = await call_tool(cat, action["tool"], action.get("args") or {})
            else:
                result = {"isError": True, "content": "reply was not one JSON object with 'tool' or 'final'"}
            emit({"event": "tool_result", "lap": lap, "tool": action.get("tool"), "isError": result["isError"],
                  "result": json.dumps(result["content"])[:600]})
            steps.append({"reply": resp["text"].strip(), "result": result})
        return finish("budget_exceeded", budget="max_iters")


async def list_tools(config_path: Path) -> dict:
    async with AsyncExitStack() as stack:
        cat = await connect(config_path, stack)
        return {"config": str(config_path.relative_to(ROOT)), "tool_count": len(cat.tools),
                "tools": {n: t["server"] for n, t in cat.tools.items()}, "servers": cat.servers,
                "resources": [r["uri"] for r in cat.resources]}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="?")
    p.add_argument("--qid")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--list-tools", action="store_true")
    p.add_argument("--log", type=Path)
    a = p.parse_args()
    config = a.config.resolve()
    if a.list_tools:
        print(json.dumps(asyncio.run(list_tools(config)), indent=1))
        return
    question = a.question
    if a.qid:
        qs = {q["id"]: q for q in map(json.loads, (W7 / "questions.jsonl").read_text().splitlines())}
        question = qs[a.qid]["question"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = a.log or W9 / "logs" / f"agent_{a.qid or 'adhoc'}_{stamp}.jsonl"
    result = asyncio.run(run_agent(question, config, log_path=log))
    print(json.dumps(result.get("output"), indent=2))
    print(f"log: {log}")


if __name__ == "__main__":
    main()
