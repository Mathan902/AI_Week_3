"""Week 7: the same migration task as a fixed workflow. Hard-coded steps, no loop.

    .venv/bin/python week7_workflow.py --qid Q01
    .venv/bin/python week7_workflow.py "How do I migrate client.request(...) to v3?"

Steps (always in this order, each at most once):
  1. LLM "extract": pull the one SDK symbol, the endpoint path and a search query out of the question
  2. search_docs(query, "v3")
  3. check_deprecation(symbol, "v3")                               skipped if no symbol
  4. get_openapi_spec(path): replacement_path from step 3, else the question's path with /v2/ -> /v3/;
     skipped if neither exists
  5. LLM "write": the output contract, from the question plus the results of steps 2-4
Same tools, model (week7_tools.MODEL) and output contract (week7_tools.CONTRACT) as week7_agent.py.
"""
from __future__ import annotations

import argparse
import json
import re
import time

from week7_tools import (CONTRACT, W7, call_llm, check_deprecation, get_openapi_spec, parse_contract,
                         search_docs)

EXTRACT_SYSTEM = """You read a developer's question about the Acme Python SDK and extract three fields.
Reply with ONE JSON object only:
{"symbol": "<the single most important SDK method, exception or parameter the question's code or text uses, or null>",
 "path": "<the API endpoint path mentioned, e.g. /v2/invoices, or null>",
 "search_query": "<a short docs search query for the v3 docs>"}"""

WRITE_SYSTEM = f"""You are a migration assistant for the Acme Python SDK. Using ONLY the tool results given,
answer the developer with SDK v3 code.
{CONTRACT}"""


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def run_workflow(question: str, llm=call_llm, echo: bool = True) -> dict:
    t0 = time.perf_counter()
    totals = {"llm_calls": 0, "tokens": 0, "cost_usd": 0.0}
    trail = []

    def llm_step(system: str, prompt: str) -> str:
        resp = llm(system, prompt)
        totals["llm_calls"] += 1
        totals["tokens"] += resp["tokens"]
        totals["cost_usd"] += resp["cost_usd"]
        return resp["text"]

    def log(step: str, detail) -> None:
        trail.append({"step": step, "detail": detail})
        if echo:
            print(json.dumps({"t": round(time.perf_counter() - t0, 2), "step": step, "detail": detail})[:300])

    # 1. extract
    plan = _json(llm_step(EXTRACT_SYSTEM, question))
    log("1 extract", plan)
    # 2. docs
    docs = search_docs(plan.get("search_query") or question, "v3")
    log("2 search_docs", [r["chunk_id"] for r in docs.get("results", [])])
    # 3. deprecation
    symbol = plan.get("symbol")
    deprecation = check_deprecation(symbol, "v3") if symbol else None
    log("3 check_deprecation", deprecation)
    # 4. spec
    path = (deprecation or {}).get("replacement_path") or (
        plan["path"].replace("/v2/", "/v3/") if isinstance(plan.get("path"), str) else None)
    spec = get_openapi_spec(path) if path else None
    log("4 get_openapi_spec", path)
    # 5. write
    evidence = {"search_docs": docs, "check_deprecation": deprecation, "get_openapi_spec": spec}
    text = llm_step(WRITE_SYSTEM, f"QUESTION:\n{question}\n\nTOOL RESULTS:\n{json.dumps(evidence)[:9000]}")
    output = parse_contract(text)
    log("5 write", "contract ok" if output else "bad contract")
    return {"system": "workflow", "status": "done" if output else "bad_final", "output": output,
            "laps": len(trail), "latency_s": round(time.perf_counter() - t0, 2), **totals}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="?")
    p.add_argument("--qid")
    a = p.parse_args()
    question = a.question
    if a.qid:
        qs = {q["id"]: q for q in map(json.loads, (W7 / "questions.jsonl").read_text().splitlines())}
        question = qs[a.qid]["question"]
    result = run_workflow(question)
    print(json.dumps({k: v for k, v in result.items() if k != "output"}))
    print(json.dumps(result["output"], indent=2))


if __name__ == "__main__":
    main()
