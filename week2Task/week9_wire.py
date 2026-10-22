"""Week 9: capture the raw JSON-RPC exchange with an MCP server over stdio. No SDK client, no model.

    .venv/bin/python week9_wire.py                                   # package-registry -> week9/wire_raw.jsonl
    .venv/bin/python week9_wire.py --server docs-search --call search_docs '{"query": "upload a file", "api_version": "v4"}'

Each line written to stdin and read from stdout is kept byte-for-byte, in order, tagged with its direction.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from mcp.client.stdio import get_default_environment

ROOT = Path(__file__).parent


def exchange(spec: dict, tool: str, args: dict, env_extra: dict | None = None) -> list[dict]:
    proc = subprocess.Popen([spec["command"], *spec.get("args", [])], cwd=ROOT, text=True, bufsize=1,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            env={**get_default_environment(), **spec.get("env", {}), **(env_extra or {})})
    wire: list[dict] = []

    def send(msg: dict) -> None:
        line = json.dumps(msg)
        wire.append({"dir": "host->server", "raw": line})
        proc.stdin.write(line + "\n")

    def recv() -> dict:
        line = proc.stdout.readline().rstrip("\n")
        wire.append({"dir": "server->host", "raw": line})
        return json.loads(line)

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "week9-wire-capture", "version": "0.1"}}})
    recv()
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    recv()
    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": tool, "arguments": args}})
    recv()
    proc.stdin.close()
    proc.wait(timeout=10)
    proc.stdout.close()
    return wire


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=ROOT / "week9" / "mcp_config.json")
    p.add_argument("--server", default="package-registry")
    p.add_argument("--call", default="get_deprecation_notices")
    p.add_argument("args", nargs="?", default='{"package": "acme-sdk", "version": "3.2"}')
    p.add_argument("--env", default="{}", help="extra env for the server, as JSON")
    p.add_argument("--out", type=Path, default=ROOT / "week9" / "wire_raw.jsonl")
    a = p.parse_args()
    spec = json.loads(a.config.read_text())["mcpServers"][a.server]
    wire = exchange(spec, a.call, json.loads(a.args), json.loads(a.env))
    a.out.write_text("".join(json.dumps(w) + "\n" for w in wire))
    for w in wire:
        print(w["dir"], w["raw"][:300])


if __name__ == "__main__":
    main()
