import json
import unittest

from week10_squad import HOP_CODE, HOP_PLAN, HOP_SYNTH, HOP_VERSION, run_squad

FINAL = {"answer": "Use `Client.send()` in v3.", "v3_code": "client.send(url='/v3/invoices', method='GET')",
         "deprecations": [{"symbol": "Client.request", "replacement": "Client.send()"}], "sources": []}


def fake_llm():
    """Plan, then each worker finishes on its first lap, then the synthesis writes the contract."""
    prompts = []

    def llm(system, prompt, timeout_s=120):
        prompts.append((system, prompt))
        if system.startswith("You are the orchestrator of a two-worker team answering"):
            text = {"target_version": "v3", "symbols": ["client.request"], "version_task": "t", "code_task": "c"}
        elif system.startswith("You are the version/deprecation worker"):
            text = {"final": {"target_version": "v3", "changes": [], "facts": "f", "sources": []}}
        elif system.startswith("You are the code-sample worker"):
            text = {"final": {"code": "x = 1", "facts": "f", "sources": []}}
        else:
            text = FINAL
        return {"text": json.dumps(text), "tokens_in": 900, "tokens_out": 100, "tokens": 1000, "cost_usd": 0.001}
    return llm, prompts


class SquadTests(unittest.TestCase):
    def test_every_llm_call_is_a_logged_handoff(self):
        llm, prompts = fake_llm()
        r = run_squad("client.request example", llm=llm, echo=False)
        self.assertEqual([h["hop"] for h in r["handoffs"]], [HOP_PLAN, HOP_VERSION, HOP_CODE, HOP_SYNTH])
        self.assertEqual(r["tokens"], sum(h["tokens"] for h in r["handoffs"]))
        self.assertEqual(r["llm_calls"], len(prompts))
        self.assertEqual(r["output"], FINAL)

    def test_code_worker_brief_carries_the_target_version(self):
        llm, prompts = fake_llm()
        run_squad("client.request example", llm=llm, echo=False)
        code_prompt = next(p for s, p in prompts if s.startswith("You are the code-sample worker"))
        self.assertIn("TARGET VERSION: v3", code_prompt)
        self.assertIn("VERSION FINDINGS:", code_prompt)

    def test_injected_500_skips_the_version_worker_and_is_logged(self):
        llm, prompts = fake_llm()
        r = run_squad("client.request example", llm=llm, inject_500=True, echo=False)
        self.assertFalse(any(s.startswith("You are the version/deprecation worker") for s, _ in prompts))
        err = [h for h in r["handoffs"] if h.get("error")]
        self.assertEqual((len(err), err[0]["hop"], err[0]["tokens"]), (1, HOP_VERSION, 0))
        self.assertIn("500", r["version_report"]["error"])
        code_prompt = next(p for s, p in prompts if s.startswith("You are the code-sample worker"))
        self.assertIn("HTTP 500", code_prompt)  # the error is passed on as-is; nothing retries it


if __name__ == "__main__":
    unittest.main()
