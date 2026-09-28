"""Week 8: the trajectory assertions, checked on fake runs (no model calls, no cost).

    .venv/bin/python -m unittest tests.test_week8_trajectory -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import week8_defenses as d  # noqa: E402
import week7_tools  # noqa: E402
from week7_agent import Budgets, run_agent  # noqa: E402
from week8_trajectory_eval import CASES, arg_problems, covered_path, score  # noqa: E402

GOOD_OUTPUT = {"answer": "ok", "v3_code": 'response = client.send(url="/v3/invoices", method="POST", body={"amount": 4200})',
               "deprecations": [{"symbol": "request", "replacement": "send"}], "sources": ["/v3/invoices"]}


def call(tool, args, result=None):
    return {"tool": tool, "args": args, "result": result if result is not None else {"path": args.get("path")}}


def docs_hit(*chunk_ids, version="v3", query="q"):
    return call("search_docs", {"query": query, "api_version": version},
                {"results": [{"chunk_id": c, "text": "..."} for c in chunk_ids]})


def fake_run(tools, status="done", output=GOOD_OUTPUT, malformed=0):
    """Build (result, calls, events) for a run whose laps were these tool calls then a final."""
    events, calls = [], []
    lap = 0
    for _ in range(malformed):
        lap += 1
        events.append({"event": "lap", "lap": lap, "tool": None, "final": False, "tokens_total": 0, "t": 0})
    for c in tools:
        lap += 1
        events.append({"event": "lap", "lap": lap, "tool": c["tool"], "args": c["args"], "final": False, "tokens_total": 0, "t": 0})
        calls.append(dict(c))
    lap += 1
    events.append({"event": "lap", "lap": lap, "tool": None, "final": True, "tokens_total": 0, "t": 0})
    result = {"status": status, "output": output if status == "done" else None, "llm_calls": lap,
              "tokens": 1000 * lap, "cost_usd": 0.001 * lap, "latency_s": 1.0 * lap}
    return result, calls, events


class ExpectedPaths(unittest.TestCase):
    def test_ten_cases_and_alternates_marked(self):
        self.assertEqual(len(CASES), 10)
        self.assertEqual(sorted(q for q, c in CASES.items() if not c.alt), ["Q09", "Q10"])
        self.assertTrue(all(c.alt for q, c in CASES.items() if q not in ("Q09", "Q10")))

    def test_order_is_not_asserted(self):
        spec_then_dep = [call("get_openapi_spec", {"path": "/v3/invoices"}),
                         call("check_deprecation", {"symbol": "client.request()", "api_version": "v3"}, {"status": "removed"})]
        self.assertIsNotNone(covered_path(CASES["Q01"], spec_then_dep))
        self.assertIsNotNone(covered_path(CASES["Q01"], spec_then_dep[::-1]))

    def test_alternate_path_via_docs_is_accepted(self):
        # Q01 without the changelog tool: the changelog PAGE plus the client page is a legitimate path
        calls = [docs_hit("v3-changelog::removed-apis::3"), docs_hit("v3-client::client-send::8-code")]
        self.assertEqual(covered_path(CASES["Q01"], calls), "docs(v3-changelog::removed-apis) + docs(v3-client::client-send)")
        # Q07 via the spec instead of the docs
        self.assertIsNotNone(covered_path(CASES["Q07"], [call("get_openapi_spec", {"path": "/v3/events"})]))

    def test_one_call_cannot_satisfy_two_matchers(self):
        one_search = [docs_hit("v3-changelog::removed-apis::3", "v3-client::client-send::8-code")]
        # a single search that happened to return both chunks still counts as ONE call matching ONE matcher
        self.assertIsNone(covered_path(CASES["Q01"], one_search))

    def test_search_that_returned_the_wrong_page_is_not_evidence(self):
        self.assertIsNone(covered_path(CASES["Q09"], [docs_hit("v3-ratelimits::handling-http-429::4")]))
        self.assertIsNotNone(covered_path(CASES["Q09"], [docs_hit("v3-webhooks::signature-verification::2-code")]))

    def test_q02_requires_the_spec(self):
        dep_only = [call("check_deprecation", {"symbol": "paginate_auto", "api_version": "v3"}, {"status": "removed"})]
        self.assertIsNone(covered_path(CASES["Q02"], dep_only))
        self.assertIsNotNone(covered_path(CASES["Q02"], dep_only + [call("get_openapi_spec", {"path": "/v3/invoices"})]))


class ArgumentValidity(unittest.TestCase):
    def test_real_arguments_pass(self):
        self.assertEqual(arg_problems("get_openapi_spec", {"path": "/v3/invoices/"}), [])
        self.assertEqual(arg_problems("check_deprecation", {"symbol": "`Client.request()`", "api_version": "v2"}), [])
        self.assertEqual(arg_problems("search_docs", {"query": "stream events", "api_version": "v3"}), [])

    def test_fluent_fiction_fails(self):
        self.assertTrue(arg_problems("get_openapi_spec", {"path": "/v3/webhooks"}))
        self.assertTrue(arg_problems("check_deprecation", {"symbol": "client.invoices.create", "api_version": "v3"}))
        self.assertTrue(arg_problems("search_docs", {"query": "x", "api_version": "v4"}))
        self.assertTrue(arg_problems("list_endpoints", {}))


class Scoring(unittest.TestCase):
    def test_right_answer_wrong_path_is_a_trajectory_failure(self):
        r, calls, events = fake_run([])  # answered from memory, zero tools
        s = score("Q08", r, calls, events)
        self.assertTrue(s["outcome_pass"])
        self.assertFalse(s["trajectory_pass"])
        self.assertIn("answer_without_evidence", s["modes"])
        self.assertEqual(s["path_str"], "F")

    def test_clean_run_passes_both(self):
        r, calls, events = fake_run([call("get_openapi_spec", {"path": "/v3/invoices"})])
        s = score("Q08", r, calls, events)
        self.assertTrue(s["outcome_pass"] and s["trajectory_pass"])
        self.assertEqual((s["modes"], s["efficiency"], s["tool_choice"], s["arg_valid"]), ([], 1.0, (1, 1), (1, 1)))

    def test_modes_are_detected(self):
        bad = [call("get_openapi_spec", {"path": "/v3/webhooks"}, {"error": "no"}),  # hallucinated + wrong tool for Q09
               docs_hit("v3-webhooks::webhooks::0"), docs_hit("v3-webhooks::webhooks::0")]  # repeated identical call
        r, calls, events = fake_run(bad, malformed=1)
        s = score("Q09", r, calls, events)
        for m in ("invalid_args", "wrong_tool", "protocol_break", "loop_thrash"):
            self.assertIn(m, s["modes"])
        self.assertFalse(s["trajectory_pass"] or s["trajectory_pass_strict"])
        self.assertEqual(s["tool_choice"], (2, 4))  # 2 of 4 action laps chose a tool in the expected set
        self.assertEqual(s["arg_valid"], (2, 3))
        self.assertEqual(s["efficiency"], 2.5)  # 5 laps vs 2 needed

    def test_malformed_lap_fails_strict_only(self):
        r, calls, events = fake_run([docs_hit("v3-webhooks::webhooks::0")], malformed=1)
        s = score("Q09", r, calls, events)
        self.assertTrue(s["trajectory_pass"])
        self.assertFalse(s["trajectory_pass_strict"])
        self.assertEqual((s["modes"], s["tool_choice"], s["efficiency"]), (["protocol_break"], (1, 2), 1.5))

    def test_no_answer_mode(self):
        r, calls, events = fake_run([docs_hit("v3-webhooks::webhooks::0")], status="budget_exceeded")
        s = score("Q09", r, calls, events)
        self.assertIn("no_answer", s["modes"])
        self.assertFalse(s["outcome_pass"])


class ArgumentValidation(unittest.TestCase):
    """The ONE mitigation: off-schema arguments get an actionable error instead of a Python TypeError."""

    def test_off_by_default_keeps_week7_behaviour(self):
        week7_tools.VALIDATE_ARGS = False
        self.assertIn("missing 2 required positional", week7_tools.run_tool("search_docs", {})["error"])

    def test_validation_restates_the_schema(self):
        week7_tools.VALIDATE_ARGS = True
        try:
            err = week7_tools.run_tool("search_docs", {})["error"]
            self.assertIn("missing 'query'", err)
            self.assertIn('"api_version": "one of [\'v2\', \'v3\']"', err)
            self.assertIn('Resend as {"tool": "search_docs"', err)
            self.assertIn("must be one of", week7_tools.run_tool("check_deprecation", {"symbol": "x", "api_version": "v4"})["error"])
            self.assertIn("unknown argument", week7_tools.run_tool("get_openapi_spec", {"path": "/v3/files", "write": 1})["error"])
            self.assertEqual(week7_tools.run_tool("get_openapi_spec", {"path": "/v3/events"})["path"], "/v3/events")
        finally:
            week7_tools.VALIDATE_ARGS = False

    def test_agent_loop_recovers_after_the_error(self):
        week7_tools.VALIDATE_ARGS = True
        replies = [{"thought": "", "tool": "get_openapi_spec", "args": {}},
                   {"thought": "", "tool": "get_openapi_spec", "args": {"path": "/v3/events"}},
                   {"thought": "", "final": GOOD_OUTPUT}]
        seen = []

        def llm(system, prompt, timeout_s=0):
            seen.append(prompt)
            return {"text": __import__("json").dumps(replies.pop(0)), "tokens": 100, "cost_usd": 0.0001}

        try:
            r = run_agent("q", Budgets(), llm=llm, echo=False)
        finally:
            week7_tools.VALIDATE_ARGS = False
        self.assertEqual((r["status"], r["laps"]), ("done", 3))
        self.assertIn("Resend as", seen[1])  # the schema error is what the model saw on lap 2


class InjectionDefences(unittest.TestCase):
    def test_sanitizer_drops_the_instruction_lines_only(self):
        text, dropped = d.sanitize_text(d.POISON_CHUNK["text"])
        self.assertEqual(dropped, 2)
        self.assertNotIn("ignore previous instructions", text)
        self.assertNotIn("verify=False", text)
        self.assertIn('client.send(url="/v3/invoices"', text)
        self.assertTrue(text.startswith("[DOCUMENT TEXT"))

    def test_scope_is_read_only(self):
        self.assertIsNone(d.scope_check("search_docs"))
        self.assertIn("read-only", d.scope_check("post_comment"))
        self.assertIn("read-only", d.scope_check("delete_docs_page"))

    def test_guardrail_blocks_tls_disable(self):
        out, why = d.guardrail({"answer": "ok", "v3_code": "client = Client(verify=False)", "deprecations": [], "sources": []})
        self.assertIsNone(out)
        self.assertIn("verify=False", why)
        out, why = d.guardrail({"answer": "You must disable TLS verification.", "v3_code": "x = 1", "deprecations": [], "sources": []})
        self.assertIsNone(out)
        self.assertEqual(d.guardrail(GOOD_OUTPUT), (GOOD_OUTPUT, None))


if __name__ == "__main__":
    unittest.main()
