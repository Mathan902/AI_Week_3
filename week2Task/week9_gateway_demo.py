"""Week 9 bonus: the gateway's denial reaching the model, and what the model does with it.

    .venv/bin/python week9_gateway_demo.py --reps 2

seeded: lap 1 is forced to be get_deprecation_notices(acme-sdk, 3.2), which the token's scope denies; the model
        drives every lap after it. free: the model drives from lap 1. Agent = week9_agent.run_agent, unchanged.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from week7_tools import call_llm
from week9_agent import W9, run_agent

CONFIG = W9 / "configs" / "gateway.json"
QUESTION = ("Our code runs on acme-sdk 3.2. List the deprecation notices the registry publishes for acme-sdk 3.2 "
            "and tell me the latest release. We still call Client(timeout_s=30).")
DENIED_CALL = {"thought": "Ask the registry for the 3.2 deprecation notices.", "tool": "get_deprecation_notices",
               "args": {"package": "acme-sdk", "version": "3.2"}}


def seeded_llm(system: str, prompt: str, timeout_s: float = 120) -> dict:
    if "TOOL RESULT:" not in prompt:
        return {"text": json.dumps(DENIED_CALL), "tokens": 0, "cost_usd": 0.0}
    return call_llm(system, prompt, timeout_s)


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=2)
    a = p.parse_args()
    for mode, llm in (("seeded", seeded_llm), ("free", call_llm)):
        for rep in range(1, a.reps + 1):
            log_path = W9 / "logs" / f"gateway_{mode}_r{rep}.jsonl"
            await run_agent(QUESTION, CONFIG, llm=llm, log_path=log_path, echo=False)
            for e in map(json.loads, log_path.read_text().splitlines()):
                if e["event"] == "lap":
                    print(mode, rep, "lap", e["lap"], e.get("tool"), json.dumps(e.get("args")), "FINAL" if e["final"] else "",
                          "|", e.get("thought", "")[:200])
                if e["event"] == "tool_result":
                    print("   ->", "isError" if e["isError"] else "ok", e["result"][:160])
                if e["event"] == "output":
                    print("   ANSWER:", json.dumps(e["output"])[:600])


if __name__ == "__main__":
    asyncio.run(main())
