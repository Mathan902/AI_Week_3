import json
import tempfile
import unittest
from pathlib import Path

from week11_app import DocsAssistant, retrieval_scope, sdk_target
from week11_logq import load, output_index
from week11_suite import check_no_deprecated_call

V2_SAMPLE = {"answer": "Use paginate_auto.", "code": "for i in client.paginate_auto(url=\"/v2/invoices\"):\n    print(i.id)",
             "sources": ["v2-pagination::paginate-auto::3-code"]}


def fake_llm(output):
    def llm(system, prompt, timeout_s=120):
        return {"text": json.dumps(output), "tokens_in": 1200, "tokens_out": 300, "tokens": 1500,
                "cost_usd": 0.0002, "api_s": 1.5, "model": "fake-haiku"}
    return llm


class TraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.bot = DocsAssistant(log_dir=cls.tmp, llm=fake_llm(V2_SAMPLE))

    def test_trace_has_what_the_drill_needs(self):
        t = self.bot.ask("how do I iterate every invoice", user_id="u-test", prompt_version="v1",
                         ts="2026-10-14T10:00:00+00:00")
        self.assertEqual([s["name"] for s in t["spans"]], ["retrieval", "tools", "generation"])
        for s in t["spans"]:
            self.assertIn("latency_ms", s)
            self.assertIn("tokens", s)
            self.assertIn("cost_usd", s)
        self.assertEqual(t["prompt_version"], "v1")
        self.assertEqual(len(t["retrieved_context_ids"]), 4)
        self.assertAlmostEqual(t["cost_usd"], 0.0002)
        self.assertEqual(load(self.tmp)[-1]["trace_id"], t["trace_id"])  # written to the day file

    def test_output_index_flags_the_deprecated_call(self):
        t = self.bot.ask("how do I iterate every invoice", prompt_version="v1", ts="2026-10-14T10:00:00+00:00")
        self.assertIn("deprecated_call_in_code", t["output_index"]["flags"])
        self.assertIn("paginate_auto()", t["output_index"]["deprecated_in_code"])

    def test_v4_scopes_retrieval_and_looks_up_the_replacement(self):
        t = self.bot.ask("how do I iterate every invoice", prompt_version="v4", ts="2026-10-14T10:00:00+00:00")
        self.assertTrue(all(c.startswith("v3-") for c in t["retrieved_context_ids"]))
        self.assertIn("check_deprecation(paginate_auto)", t["spans"][1]["attrs"]["calls"])
        self.assertIn("get_openapi_spec(/v3/invoices)", t["spans"][1]["attrs"]["calls"])


class PureTests(unittest.TestCase):
    def test_scope(self):
        self.assertEqual(retrieval_scope("how do I iterate every invoice"), "v3")
        self.assertEqual(retrieval_scope("I'm still on SDK v2, how do I iterate every invoice"), "v2")
        self.assertIsNone(retrieval_scope("v2 upload limit vs v3"))
        self.assertEqual(sdk_target("what was the old default backoff"), "v3")

    def test_contradiction_flag_needs_the_symbol_missing_from_v2_context(self):
        trace = {"output": {"code": "client = Client(timeout_s=120)"}, "sdk_target": "v3",
                 "retrieved_context_ids": ["v3-changelog::timeout-units-renamed::2"]}
        self.assertEqual(output_index(trace, {})["flags"], ["deprecated_call_in_code", "code_contradicts_context"])

    def test_no_deprecated_call_checks_only_the_code_block(self):
        case = {"code_must_not": [r"\bpaginate_auto\b"]}
        prose_only = "paginate_auto was removed in v3.\n\n```python\nfor p in client.list_after(url='/v3/invoices'):\n    pass\n```"
        self.assertEqual(check_no_deprecated_call(prose_only, case)[0], "pass")
        in_code = "Removed in v3.\n\n```python\nfor i in client.paginate_auto():\n    pass\n```"
        self.assertEqual(check_no_deprecated_call(in_code, case)[0], "fail")
        self.assertEqual(check_no_deprecated_call(in_code, {})[0], "n/a")


if __name__ == "__main__":
    unittest.main()
