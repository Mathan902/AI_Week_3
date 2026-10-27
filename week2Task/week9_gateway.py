"""Week 9 bonus: one MCP front door for both servers, with an audit line per tools/call and token scopes.

    (launched by the host from week9/configs/gateway.json; speaks MCP on stdio like any server)

To the agent this is just one more MCP server, so switching to it is again a config edit. Behind it:
  GATEWAY_UPSTREAMS  an MCP config ({"mcpServers": ...}) naming the real servers; the gateway is their client
  GATEWAY_TOKEN      the caller's token. Only its sha256 is stored, in GATEWAY_SCOPES
  GATEWAY_SCOPES     {"tokens": {sha256: {"caller": name, "deny": [tool, ...]}}}
  GATEWAY_AUDIT_LOG  one JSON line per tools/call: caller, tool, server, package@version, decision

A denied tool stays in tools/list (the caller can see it exists) but a call to it returns isError with a
message that says it is a permission decision, not an outage, and which tools the token CAN use.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from contextlib import AsyncExitStack
from pathlib import Path

import mcp.types as types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

ROOT = Path(__file__).parent
UPSTREAMS = ROOT / os.environ.get("GATEWAY_UPSTREAMS", "week9/configs/server1_plus_2.json")
SCOPES = ROOT / os.environ.get("GATEWAY_SCOPES", "week9/gateway_scopes.json")
AUDIT = ROOT / os.environ.get("GATEWAY_AUDIT_LOG", "week9/logs/gateway_audit.log")
TOKEN = os.environ.get("GATEWAY_TOKEN", "")
# The docs-search tools have no package argument: they are the docs of this one package.
DEFAULT_PACKAGE = "acme-sdk"


def caller_scope() -> dict:
    tokens = json.loads(SCOPES.read_text())["tokens"]
    digest = hashlib.sha256(TOKEN.encode()).hexdigest()
    # An unknown or missing token gets a scope that denies everything.
    return tokens.get(digest, {"caller": "unknown-token", "deny": ["*"]})


def requested(args: dict) -> str:
    package = args.get("package") or DEFAULT_PACKAGE
    version = args.get("version") or args.get("api_version") or "*"
    return f"{package}@{version}"


def audit(**fields) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **fields}) + "\n")


async def main() -> None:
    scope = caller_scope()
    routes: dict[str, tuple[ClientSession, str, str]] = {}   # exposed name -> (session, server, upstream name)
    tools: list[types.Tool] = []
    async with AsyncExitStack() as stack:
        devnull = stack.enter_context(open(os.devnull, "w"))
        for server, spec in json.loads(UPSTREAMS.read_text())["mcpServers"].items():
            params = StdioServerParameters(command=spec["command"], args=spec.get("args", []),
                                           env={**get_default_environment(), **spec.get("env", {})},
                                           cwd=str(ROOT / spec.get("cwd", ".")))
            read, write = await stack.enter_async_context(stdio_client(params, errlog=devnull))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            for tool in (await session.list_tools()).tools:
                exposed = tool.name if tool.name not in routes else f"{server}.{tool.name}"
                routes[exposed] = (session, server, tool.name)
                tools.append(tool.model_copy(update={"name": exposed}))

        def allowed(name: str) -> bool:
            return "*" not in scope["deny"] and name not in scope["deny"]

        gateway = Server("mcp-gateway", instructions="One front door for docs-search and package-registry.")

        @gateway.list_tools()
        async def list_tools() -> list[types.Tool]:
            return tools

        @gateway.call_tool(validate_input=False)  # the upstream server validates its own arguments
        async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
            line = {"caller": scope["caller"], "tool": name, "requested": requested(arguments)}
            if name not in routes:
                audit(**line, server=None, decision="unknown_tool")
                return types.CallToolResult(isError=True, content=[types.TextContent(
                    type="text", text=f"unknown tool {name!r}; tools are {sorted(routes)}")])
            session, server, upstream_name = routes[name]
            if not allowed(name):
                audit(**line, server=server, decision="denied")
                ok = sorted(n for n in routes if allowed(n))
                return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=(
                    f"denied: caller {scope['caller']!r} is not permitted to call {name}. This is a permission "
                    f"decision by the gateway, not an outage and not a missing package or version, so retrying "
                    f"will not help. Tools this caller may use: {ok}. For deprecations of acme-sdk use "
                    f"check_deprecation(symbol, api_version=\"v3\"); version lookups (get_package_versions, "
                    f"get_release_info) still work."))])
            result = await session.call_tool(upstream_name, arguments)
            audit(**line, server=server, decision="allowed", isError=bool(result.isError))
            return result

        async with stdio_server() as (read, write):
            await gateway.run(read, write, gateway.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
