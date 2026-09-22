import json
import time
import unittest

from week7_agent import Budgets, run_agent


def fake_llm(tokens=1000, cost=0.001, sleep=0.0, final_after=None):
    """An LLM stub that keeps calling a tool (a spinning agent) unless final_after is set."""
    calls = {"n": 0}

    def llm(system, prompt, timeout_s=120):
        calls["n"] += 1
        if sleep:
            if sleep > timeout_s:
                raise TimeoutError(f"LLM call exceeded {timeout_s:.1f}s")
            time.sleep(sleep)
        if final_after and calls["n"] >= final_after:
            text = json.dumps({"final": {"answer": "a", "v3_code": "x = 1", "deprecations": [], "sources": []}})
        else:
            text = json.dumps({"thought": "again", "tool": "get_openapi_spec", "args": {"path": "/v3/events"}})
        return {"text": text, "tokens": tokens, "cost_usd": cost, "latency_s": sleep}
    return llm, calls


class BudgetTests(unittest.TestCase):
    def run_(self, budgets, **kw):
        llm, calls = fake_llm(**kw)
        return run_agent("q", budgets, llm=llm, echo=False), calls["n"]

    def test_max_iters(self):
        r, n = self.run_(Budgets(max_iters=3))
        self.assertEqual((r["status"], r["budget"], n), ("budget_exceeded", "max_iters", 3))

    def test_max_tokens(self):
        r, n = self.run_(Budgets(max_tokens=5000), tokens=2000)
        self.assertEqual((r["status"], r["budget"]), ("budget_exceeded", "max_tokens"))
        self.assertLessEqual(r["tokens"], 5000)  # the pre-lap check refuses the lap that would cross it

    def test_max_cost(self):
        r, n = self.run_(Budgets(max_cost_usd=0.0025), cost=0.001)
        self.assertEqual((r["status"], r["budget"]), ("budget_exceeded", "max_cost_usd"))
        self.assertLessEqual(r["cost_usd"], 0.0025)

    def test_max_wall(self):
        r, n = self.run_(Budgets(max_wall_s=0.25), sleep=0.1)
        self.assertEqual((r["status"], r["budget"]), ("budget_exceeded", "max_wall_s"))
        self.assertLess(r["latency_s"], 0.5)

    def test_finishes_inside_budgets(self):
        r, n = self.run_(Budgets(), final_after=2)
        self.assertEqual((r["status"], r["laps"], r["tokens"]), ("done", 2, 2000))  # every lap's tokens summed


if __name__ == "__main__":
    unittest.main()
