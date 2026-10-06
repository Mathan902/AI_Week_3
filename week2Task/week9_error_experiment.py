"""Week 9 Set E, requirement 5: the same failing call, old docstring/error (DOCS_PROMPTS=v1) vs new (v2).

    .venv/bin/python week9_error_experiment.py --reps 3

Two modes per condition, docs-search server only so the docstring is the only variable:
  seeded: lap 1 is FORCED to be the identical failing call search_docs(api_version="v4"); the model drives every
          lap after that, so both conditions handle exactly the same error. Lap 1 costs nothing (no model call).
  free:   the model drives from lap 1, to see whether the docstring alone keeps it from making the call.
The agent itself is week9_agent.run_agent, unchanged; only the config and the llm callable differ.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from week7_tools import call_llm
from week9_agent import W9, run_agent

QUESTION = ("We're upgrading to acme-sdk v4 next sprint. Using the v4 docs, show me how to upload report.pdf "
            "with the v4 client.")
FAILING_CALL = {"thought": "The developer wants the v4 docs, so search them.", "tool": "search_docs",
                "args": {"query": "upload a file", "api_version": "v4"}}
OUT = W9 / "error_experiment"


def seeded_llm(system: str, prompt: str, timeout_s: float = 120) -> dict:
    if "TOOL RESULT:" not in prompt:  # the first lap: no tool has run yet
        return {"text": json.dumps(FAILING_CALL), "tokens": 0, "cost_usd": 0.0}
    return call_llm(system, prompt, timeout_s)


def score(log: list[dict]) -> dict:
    laps = [e for e in log if e["event"] == "lap"]
    calls = [(e["tool"], (e.get("args") or {}).get("api_version")) for e in laps if e.get("tool")]
    out = next((e["output"] for e in log if e["event"] == "output"), None) or {}
    code, answer = out.get("v3_code", ""), out.get("answer", "")
    return {
        "v4_calls": sum(1 for t, v in calls if t == "search_docs" and v and "4" in v),
        "retried_v3_after_error": any(t == "search_docs" and v == "v3" for t, v in calls[1:]),
        "used_v2_docs": any(t == "search_docs" and v == "v2" for t, v in calls),
        "code_uses_v2_api": bool(re.search(r"upload_file\(|\.request\(|paginate_auto", code)),
        "code_uses_v3_upload": "files.upload" in code,
        "says_v4_unpublished": bool(re.search(r"v4[^.]*(not|no|isn't|doesn't|does not|hasn't)[^.]*"
                                              r"(exist|publish|releas|availab|document)", answer, re.I)),
        "laps": len(laps), "tools": [t for t, _ in calls],
    }


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--modes", default="seeded,free")
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in a.modes.split(","):
        for prompts in ("v1", "v2"):
            config = W9 / "configs" / f"docs_only_prompts_{prompts}.json"
            for rep in range(1, a.reps + 1):
                log_path = OUT / f"{mode}_{prompts}_r{rep}.jsonl"
                await run_agent(QUESTION, config, llm=seeded_llm if mode == "seeded" else call_llm,
                                log_path=log_path, echo=False)
                log = [json.loads(l) for l in log_path.read_text().splitlines()]
                end = next(e for e in log if e["event"] == "end")
                row = {"mode": mode, "prompts": prompts, "rep": rep, "status": end["status"],
                       "cost_usd": round(end["cost_usd"], 4), **score(log)}
                rows.append(row)
                print(json.dumps(row))
    (OUT / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


if __name__ == "__main__":
    asyncio.run(main())
