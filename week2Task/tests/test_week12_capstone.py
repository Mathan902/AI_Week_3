"""Week 12: the integrated engine's guards and seams, with a scripted fake LLM (no model cost).

    .venv/bin/python -m unittest tests.test_week12_capstone -v

The MCP tests start the real week12_server.py over stdio, so the trace-id hop, the version pin and the redaction are
exercised through the same JSON-RPC path production uses. Only the model is fake.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import week12_guards as g  # noqa: E402
from week12_engine import Engine  # noqa: E402


def scripted(*replies):
    """A fake call_llm that returns the given replies in order and records every prompt it was sent."""
    sent = []

    def llm(system, prompt, timeout_s=0):
        sent.append({"system": system, "prompt": prompt})
        text = replies[min(len(sent) - 1, len(replies) - 1)]
        return {"text": text if isinstance(text, str) else json.dumps(text), "tokens_in": 100, "tokens_out": 20,
                "tokens": 120, "cost_usd": 0.0001, "latency_s": 0.01, "api_s": 0.01, "model": "fake"}
    llm.sent = sent
    return llm


def final(answer, code="", sources=(), deprecations=()):
    return {"thought": "done", "final": {"answer": answer, "code": code, "deprecations": list(deprecations),
                                         "sources": list(sources)}}


class Guards(unittest.TestCase):
    def test_v3_code_fails_the_v2_symbol_table(self):
        r = g.check_code('from acme import Client\nclient = Client(timeout_ms=1)\nclient.send(url="/v3/invoices")', "v2")
        self.assertEqual(r["status"], "fail")
        self.assertTrue(any("client.send()" in v and "exists in v3" in v for v in r["violations"]))
        self.assertTrue(any("timeout_ms" in v for v in r["violations"]))

    def test_v2_code_passes_v2_and_fails_v3(self):
        code = 'for i in client.paginate_auto(url="/v2/invoices", page_size=50):\n    print(i.id)'
        self.assertEqual(g.check_code(code, "v2")["status"], "pass")
        self.assertEqual(g.check_code(code, "v3")["status"], "fail")

    def test_invented_method_and_parameter_are_caught(self):
        self.assertIn("client.batch()", g.check_code("client.batch(requests=[])", "v2")["violations"][0])
        self.assertIn("no parameter", g.check_code('client.send(url="/v3/x", timeout=5)', "v3")["violations"][0])

    def test_imports_must_resolve_in_that_version(self):
        r = g.check_code("from acme.errors import RateLimitError", "v2")
        self.assertEqual(r["status"], "fail")
        self.assertEqual(g.check_code("from acme.errors import TooManyRequestsError", "v2")["status"], "pass")
        self.assertEqual(g.check_code("from acme.webhooks import verify_signature", "v2")["status"], "fail")

    def test_unparseable_code_fails(self):
        self.assertEqual(g.check_code("client.send(url=", "v3")["status"], "fail")

    def test_version_resolution_precedence(self):
        self.assertEqual(g.resolve_version("how do I paginate", "2.4").major, "v2")       # IDE flag
        self.assertEqual(g.resolve_version("I'm on 2.4, how do I paginate").minor, "2.4")  # stated in text
        fp = g.resolve_version('client.paginate_auto(url="/v2/invoices") is slow')
        self.assertEqual((fp.major, fp.source), ("v2", "code_fingerprint"))
        self.assertEqual(g.resolve_version("how do I paginate").source, "default")
        mig = g.resolve_version("migrate my paginate_auto loop to 3.0", "2.4")
        self.assertEqual((mig.major, mig.code_target, mig.migration), ("v2", "v3", True))
        v4 = g.resolve_version("what's new in SDK v4?")
        self.assertEqual((v4.major, v4.unsupported), ("v3", "4.x"))

    def test_redaction(self):
        text, kinds = g.redact("key acme_live_9f8a7b6c5d4e3f2a1b0c db postgres://admin:hunter2@h:5432/p "
                               "ACME_API_TOKEN=sk-live-abcdef1234567890XYZ Bearer abcdefghijklmnopqrst")
        for secret in ("acme_live_9f8a7b6c5d4e3f2a1b0c", "hunter2", "sk-live-abcdef1234567890XYZ", "abcdefghijklmnopqrst"):
            self.assertNotIn(secret, text)
        self.assertIn("ACME_API_TOKEN=", text)  # the variable name survives: it is the answer to "how do I set it"
        self.assertEqual(set(kinds), {"acme_token", "connection_string", "api_key", "bearer_token"})

    def test_redaction_never_corrupts_code_that_references_a_secret(self):
        """The Week 12 closed loop (C18, tr-5871db30a290): policy v1 made this sample unparseable."""
        code = ('import os\nfrom acme.webhooks import verify_signature\n\n'
                'WEBHOOK_SIGNING_SECRET = os.environ["ACME_WEBHOOK_SECRET"]\n'
                'verify_signature(payload=b"", signature_header="h", secret=WEBHOOK_SIGNING_SECRET)\n'
                'token = os.getenv("ACME_API_TOKEN")\n')
        redacted, kinds = g.redact(code)
        self.assertEqual(redacted, code)
        self.assertEqual(kinds, [])
        self.assertEqual(g.check_code(redacted, "v3")["status"], "pass")
        self.assertIn("[REDACTED", g.redact('API_KEY = "9f8a7b6c5d4e3f2a1b0c"')[0])  # literals still go


class DocsDrift(unittest.TestCase):
    """The cases that go red the morning the docs change (v3.1 ships with two more deprecations)."""

    def test_symbol_table_matches_snapshot(self):
        snap = json.loads((ROOT / "week12" / "symbols_snapshot.json").read_text())
        self.assertEqual({v: g.SYMBOLS[v].to_json() for v in g.SYMBOLS}, snap,
                         "the docs changed the SDK surface: review week12_guards.SYMBOLS, then re-snapshot")

    def test_every_changelog_entry_is_guarded_by_an_eval_case(self):
        cases = [json.loads(l) for l in (ROOT / "week12" / "eval_cases.jsonl").read_text().splitlines() if l.strip()]
        noticed = {s.lower() for c in cases for s in c["must_notice"]}
        for e in g.CHANGELOG + g.DOCS_ONLY_RENAMES:
            names = {a.split(".")[-1].lower() for a in [e["symbol"], *e["aliases"]]}
            self.assertTrue(names & noticed, f"changelog entry {e['symbol']} has no eval case that must surface it")


class ThroughMcp(unittest.TestCase):
    """Fake model, real MCP server process."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.config = cls.tmp / "mcp.json"
        cls.config.write_text(json.dumps({"mcpServers": {"acme-docs": {
            "command": str(ROOT / ".venv" / "bin" / "python"), "args": [str(ROOT / "week12_server.py")],
            "env": {"W12_LOG_DIR": str(cls.tmp / "logs")}}}}))

    def ask(self, llm, question, flag, release="r2"):
        async def go():
            async with Engine(release, llm=llm, log_dir=self.tmp / "logs", label="test", config=self.config) as eng:
                return await eng.ask(question, flag)
        return asyncio.run(go())

    def test_tools_are_discovered_not_hardcoded(self):
        t = self.ask(scripted(final("ok")), "hi", "3.0")
        self.assertEqual(set(t["tools_discovered"]),
                         {"search_docs", "check_deprecation", "symbol_exists", "get_openapi_spec"})

    def test_one_trace_id_survives_the_mcp_hop_and_secrets_never_land(self):
        secret = "acme_live_9f8a7b6c5d4e3f2a1b0c"
        llm = scripted({"thought": "s", "tool": "search_docs", "args": {"query": "set api token", "sdk_version": "2.4"}},
                       final("Set ACME_API_TOKEN.", sources=["v2-client::authentication::1"]))
        t = self.ask(llm, f"my token {secret} fails, how do I set it?", "2.4")
        self.assertTrue(t["trace_propagation"]["all_match"])
        server_lines = [json.loads(l) for f in (self.tmp / "logs").glob("mcp_server-*.jsonl")
                        for l in f.read_text().splitlines()]
        self.assertIn(t["trace_id"], {s["trace_id"] for s in server_lines})
        self.assertNotIn(secret, json.dumps(llm.sent))               # the model never saw it
        for f in (self.tmp / "logs").glob("*.jsonl"):                 # neither log did
            self.assertNotIn(secret, f.read_text())

    def test_host_pins_retrieval_to_the_callers_version(self):
        llm = scripted({"thought": "s", "tool": "search_docs", "args": {"query": "paginate", "sdk_version": "3.0"}},
                       final("Use paginate_auto().", 'for i in client.paginate_auto(url="/v2/invoices"):\n    print(i)'))
        t = self.ask(llm, "how do I paginate", "2.4")
        call = t["tool_calls"][0]
        self.assertEqual(call["enforced"], {"from": "3.0", "to": "2.4"})
        self.assertTrue(all(r["sdk_version"] == "v2" for r in call["result"]["results"]))

    def test_r1_does_not_pin(self):
        llm = scripted({"thought": "s", "tool": "search_docs", "args": {"query": "paginate", "sdk_version": "3.0"}},
                       final("x"))
        t = self.ask(llm, "how do I paginate", "2.4", release="r1")
        self.assertIsNone(t["tool_calls"][0]["enforced"])
        self.assertTrue(all(r["sdk_version"] == "v3" for r in t["tool_calls"][0]["result"]["results"]))

    def test_wrong_version_code_gets_one_repair_then_is_withheld(self):
        v3 = final("Use list_after().", 'page = client.list_after(url="/v3/invoices", cursor=None)')
        llm = scripted(v3, v3)
        t = self.ask(llm, "how do I paginate", "2.4")
        self.assertEqual(t["repairs"], 1)
        self.assertIn("HOST CODE CHECK", llm.sent[1]["prompt"])
        self.assertEqual(t["output"]["code"], "")
        self.assertIn("withheld", t["answer_text"])

    def test_deprecation_surfaced_unasked_for_v2_caller(self):
        llm = scripted(final("Use paginate_auto().", 'for i in client.paginate_auto(url="/v2/invoices"):\n    print(i)'))
        t = self.ask(llm, "how do I paginate", "2.4")
        self.assertTrue(any(n.get("symbol") == "paginate_auto" and "3.0" in n["text"] for n in t["notes"]))

    def test_ungrounded_citations_are_dropped(self):
        t = self.ask(scripted(final("x", sources=["v3-client::client-send::5"])), "send", "3.0")
        self.assertEqual(t["citations"], [])
        self.assertEqual(t["dropped_citations"], ["v3-client::client-send::5"])


if __name__ == "__main__":
    unittest.main()
