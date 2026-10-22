"""Week 9: MCP discovery, the config-only server swap, the recoverable error and the gateway's scopes.

    .venv/bin/python -m unittest tests.test_week9_mcp -v

Real MCP servers over stdio, a scripted fake model: no model calls, no cost.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from week9_agent import W9, list_tools, run_agent  # noqa: E402
from week9_wire import exchange  # noqa: E402

AGENT = Path(__file__).resolve().parent.parent / "week9_agent.py"
CONFIGS = W9 / "configs"
GOOD_FINAL = {"answer": "ok", "v3_code": "x = 1", "deprecations": [], "sources": []}


def scripted(*replies):
    """A fake model that returns the given replies in order."""
    queue = [json.dumps(r) for r in replies]

    def llm(system, prompt, timeout_s=120):
        return {"text": queue.pop(0), "tokens": 0, "cost_usd": 0.0}
    return llm


def wire_result(config: str, server: str, tool: str, args: dict) -> dict:
    spec = json.loads((CONFIGS / config).read_text())["mcpServers"][server]
    return json.loads(exchange(spec, tool, args)[-1]["raw"])["result"]


class Discovery(unittest.TestCase):
    def test_agent_hard_codes_no_tool_or_server_name(self):
        src = AGENT.read_text()
        for name in ("search_docs", "get_openapi_spec", "check_deprecation", "get_package_versions",
                     "get_release_info", "get_deprecation_notices", "package-registry", "docs-search"):
            self.assertNotIn(name, src, f"{name} is hard-coded in the agent")

    def test_tool_count_comes_from_config(self):
        one = asyncio.run(list_tools(CONFIGS / "server1.json"))
        two = asyncio.run(list_tools(CONFIGS / "server1_plus_2.json"))
        self.assertEqual(one["tool_count"], 3)
        self.assertEqual(two["tool_count"], 6)
        self.assertEqual(set(two["tools"]) - set(one["tools"]),
                         {"get_package_versions", "get_release_info", "get_deprecation_notices"})
        self.assertEqual(one["resources"], ["docs://version-support-matrix"])

    def test_agent_routes_a_registry_call_to_the_registry_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.jsonl"
            llm = scripted({"tool": "get_release_info", "args": {"package": "acme-sdk", "version": "3"}},
                           {"final": GOOD_FINAL})
            result = asyncio.run(run_agent("q", CONFIGS / "server1_plus_2.json", llm=llm, log_path=log, echo=False))
            events = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(result["status"], "done")
        lap = next(e for e in events if e["event"] == "lap" and e["tool"])
        self.assertEqual(lap["server"], "package-registry")
        tool_result = next(e for e in events if e["event"] == "tool_result")
        self.assertFalse(tool_result["isError"])
        self.assertIn("2026-08-18", tool_result["result"])


class RecoverableError(unittest.TestCase):
    ARGS = {"query": "upload a file", "api_version": "v4"}

    def test_v1_error_is_opaque(self):
        r = wire_result("docs_only_prompts_v1.json", "docs-search", "search_docs", self.ARGS)
        self.assertTrue(r["isError"])
        self.assertTrue(r["content"][0]["text"].endswith("Error 3"))

    def test_v2_error_says_what_exists_and_what_to_call_next(self):
        r = wire_result("docs_only_prompts_v2.json", "docs-search", "search_docs", self.ARGS)
        text = r["content"][0]["text"]
        self.assertTrue(r["isError"])
        self.assertIn("no docs for v4.x", text)
        self.assertIn("not an outage", text)
        self.assertRegex(text, r'search_docs\(query=.*api_version="v3"\)')


class Gateway(unittest.TestCase):
    def test_one_front_door_exposes_both_servers(self):
        cat = asyncio.run(list_tools(CONFIGS / "gateway.json"))
        self.assertEqual(cat["tool_count"], 6)
        self.assertEqual(set(cat["tools"].values()), {"gateway"})

    def test_scoped_token_denies_deprecations_but_allows_version_lookup(self):
        audit = W9 / "logs" / "gateway_audit.log"
        before = len(audit.read_text().splitlines()) if audit.exists() else 0
        denied = wire_result("gateway.json", "gateway", "get_deprecation_notices",
                             {"package": "acme-sdk", "version": "3.2"})
        allowed = wire_result("gateway.json", "gateway", "get_release_info", {"package": "acme-sdk", "version": "3"})
        self.assertTrue(denied["isError"])
        self.assertIn("permission decision", denied["content"][0]["text"])
        self.assertIn("get_release_info", denied["content"][0]["text"])  # names what IS allowed
        self.assertFalse(allowed["isError"])
        lines = [json.loads(line) for line in audit.read_text().splitlines()[before:]]
        self.assertEqual([(l["tool"], l["requested"], l["decision"]) for l in lines],
                         [("get_deprecation_notices", "acme-sdk@3.2", "denied"),
                          ("get_release_info", "acme-sdk@3", "allowed")])
        self.assertTrue(all(l["caller"] == "docs-assistant" for l in lines))


if __name__ == "__main__":
    unittest.main()
