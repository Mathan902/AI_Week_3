"""Week 10: the docs squad. One orchestrator, two narrow workers, every hand-off logged with its tokens.

    .venv/bin/python week10_squad.py "client.request example"
    .venv/bin/python week10_squad.py --inject-500 "client.request example"   # version worker returns HTTP 500

Hops, always in this order (the code worker needs the version worker's target version, so they cannot
run in parallel):
  1. user -> orchestrator (plan)            one LLM call: target version, symbols, the two sub-tasks
  2. orchestrator -> version worker         a small loop, tools: check_deprecation, search_docs
  3. orchestrator -> code-sample worker     a small loop, tools: search_docs, get_openapi_spec
  4. workers -> orchestrator (synthesis)    one LLM call: the Week 7 output contract

Each worker gets a brief, not the whole conversation: the question, the target version and (for the code
worker) the version worker's compact findings. Every lap of a worker re-sends its brief plus its own
earlier laps, so each lap is logged as its own hand-off record with the tokens it was billed for.

Same model, tools, output contract and thinking setting as the single agent (week7_agent.py).
"""
from __future__ import annotations

import argparse
import json
import time

from week7_tools import CONTRACT, TOOLS, LLMError, call_llm, parse_contract, run_tool

HOP_PLAN = "user -> orchestrator (plan)"
HOP_VERSION = "orchestrator -> version worker"
HOP_CODE = "orchestrator -> code-sample worker"
HOP_SYNTH = "workers -> orchestrator (synthesis)"
WORKER_MAX_LAPS = 4

PLAN_SYSTEM = """You are the orchestrator of a two-worker team answering developer questions about the Acme Python SDK.
Split the question for your workers. Reply with ONE JSON object only:
{"target_version": "v2" or "v3" (the SDK version the developer's code will run on; v3 unless the question says otherwise),
 "symbols": ["<SDK methods, exceptions or parameters the question names>"],
 "version_task": "<what the version/deprecation worker must establish>",
 "code_task": "<the code sample the code-sample worker must write, or null if no code is needed>"}"""


def _tools(names: list[str]) -> str:
    return json.dumps([t for t in TOOLS if t["name"] in names], indent=1)


VERSION_TOOLS = ["check_deprecation", "search_docs"]
CODE_TOOLS = ["search_docs", "get_openapi_spec"]

VERSION_SYSTEM = f"""You are the version/deprecation worker for the Acme Python SDK. Your only job: for the given symbols and
question, establish which SDK version applies and what was removed, renamed or changed between v2 and v3. Do not write code.
Each reply is exactly ONE JSON object:
  {{"thought": "<why>", "tool": "<tool name>", "args": {{...}}}}   to call one tool, or
  {{"thought": "<why>", "final": {{"target_version": "v2|v3", "changes": [{{"symbol": "...", "status": "...", "replacement": "..."}}],
     "facts": "<1-3 sentences of version facts from tool results>", "sources": ["<chunk_id or changelog source>"]}}}}
Tools:
{_tools(VERSION_TOOLS)}"""

CODE_SYSTEM = f"""You are the code-sample worker for the Acme Python SDK. Your only job: write a short, runnable Python sample for
the target SDK version, using only calls that appear in tool results. Respect the version findings you are given.
Each reply is exactly ONE JSON object:
  {{"thought": "<why>", "tool": "<tool name>", "args": {{...}}}}   to call one tool, or
  {{"thought": "<why>", "final": {{"code": "<python, newlines as \\n, or empty if no code applies>",
     "facts": "<1-3 sentences: the fact the developer asked for, from tool results>", "sources": ["<chunk_id or spec path>"]}}}}
Tools:
{_tools(CODE_TOOLS)}"""

SYNTH_SYSTEM = f"""You are the orchestrator of a two-worker team for the Acme Python SDK. Using ONLY your workers' reports, write
the answer for the developer.
{CONTRACT}"""


def parse_action(text: str) -> dict:
    """The first JSON object in a reply, or {}."""
    start = text.find("{")
    if start < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def run_squad(question: str, llm=call_llm, inject_500: bool = False, echo: bool = True) -> dict:
    t0 = time.perf_counter()
    handoffs: list[dict] = []        # one record per LLM call, labelled with the hand-off it belongs to
    seen: list[dict] = []            # every tool result any worker saw, for the judge's "documentation shown"
    events: list[dict] = []

    def emit(event: dict) -> None:
        event = {"t": round(time.perf_counter() - t0, 2), **event}
        events.append(event)
        if echo:
            print(json.dumps(event)[:300])

    def hop_call(hop: str, lap: int, system: str, prompt: str) -> str:
        resp = llm(system, prompt)
        handoffs.append({"hop": hop, "lap": lap, "brief_chars": len(prompt), "tokens_in": resp.get("tokens_in", 0),
                         "tokens_out": resp.get("tokens_out", 0), "tokens": resp["tokens"],
                         "cost_usd": resp["cost_usd"], "latency_s": round(resp.get("latency_s", 0.0), 2)})
        emit({"event": "handoff", **handoffs[-1]})
        return resp["text"]

    def run_worker(hop: str, system: str, allowed: list[str], brief: str) -> dict:
        steps: list[str] = []
        for lap in range(1, WORKER_MAX_LAPS + 1):
            prompt = "\n".join([brief, *steps, "Reply with the next JSON object."])
            reply = hop_call(hop, lap, system, prompt)
            action = parse_action(reply)
            emit({"event": "worker_lap", "hop": hop, "lap": lap, "tool": action.get("tool"), "args": action.get("args"),
                  "final": "final" in action, **({} if action else {"unparsed_reply": reply[:300]})})
            if isinstance(action.get("final"), dict):
                return action["final"]
            if action.get("tool") in allowed:
                result = run_tool(action["tool"], action.get("args") or {})
                seen.append({"tool": action["tool"], "args": action.get("args"), "result": result})
            elif action.get("tool"):
                result = {"error": f"tool {action['tool']!r} is not available to this worker; use one of {allowed}"}
            else:
                result = {"error": "reply was not one JSON object with 'tool' or 'final'"}
            steps.append(f"YOU:\n{json.dumps(action)}\nTOOL RESULT:\n{json.dumps(result)[:3000]}\n")
        return {"error": f"no final after {WORKER_MAX_LAPS} laps"}

    def finish(status: str, output: dict | None, **extra) -> dict:
        totals = {"llm_calls": len(handoffs), "tokens": sum(h["tokens"] for h in handoffs),
                  "cost_usd": sum(h["cost_usd"] for h in handoffs)}
        result = {"system": "squad", "status": status, "output": output, "handoffs": handoffs, "seen": seen,
                  "events": events, "latency_s": round(time.perf_counter() - t0, 2), **totals, **extra}
        emit({"event": "end", "status": status, **totals})
        return result

    try:
        # 1. plan
        plan = parse_action(hop_call(HOP_PLAN, 1, PLAN_SYSTEM, f"QUESTION:\n{question}"))
        target = plan.get("target_version") if plan.get("target_version") in ("v2", "v3") else "v3"
        emit({"event": "plan", "plan": plan})

        # 2. version/deprecation worker
        if inject_500:
            version = {"status": 500, "error": "HTTP 500 Internal Server Error from version/deprecation worker"}
            handoffs.append({"hop": HOP_VERSION, "lap": 0, "brief_chars": 0, "tokens_in": 0, "tokens_out": 0,
                             "tokens": 0, "cost_usd": 0.0, "latency_s": 0.0, "error": version["error"]})
            emit({"event": "worker_error", "hop": HOP_VERSION, **version})
        else:
            version = run_worker(HOP_VERSION, VERSION_SYSTEM, VERSION_TOOLS,
                                 f"QUESTION:\n{question}\nTARGET VERSION (orchestrator's guess): {target}\n"
                                 f"SYMBOLS: {json.dumps(plan.get('symbols') or [])}\n"
                                 f"YOUR TASK: {plan.get('version_task') or 'check every symbol for v2->v3 changes'}")
        emit({"event": "worker_result", "hop": HOP_VERSION, "result": version})
        target = version.get("target_version") if version.get("target_version") in ("v2", "v3") else target

        # 3. code-sample worker: gets the target version and the version findings, not the whole history
        code = run_worker(HOP_CODE, CODE_SYSTEM, CODE_TOOLS,
                          f"QUESTION:\n{question}\nTARGET VERSION: {target}\n"
                          f"VERSION FINDINGS: {json.dumps(version)}\n"
                          f"YOUR TASK: {plan.get('code_task') or 'state the fact asked for; code only if it helps'}")
        emit({"event": "worker_result", "hop": HOP_CODE, "result": code})

        # 4. synthesis
        text = hop_call(HOP_SYNTH, 1, SYNTH_SYSTEM,
                        f"QUESTION:\n{question}\nTARGET VERSION: {target}\n"
                        f"VERSION/DEPRECATION WORKER REPORT:\n{json.dumps(version)}\n"
                        f"CODE-SAMPLE WORKER REPORT:\n{json.dumps(code)}")
    except LLMError as exc:
        return finish("error", None, detail=str(exc))
    output = parse_contract(text)
    return finish("done" if output else "bad_final", output, plan=plan, version_report=version, code_report=code)


def main() -> None:
    import week7_tools
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--inject-500", action="store_true")
    a = p.parse_args()
    week7_tools.THINKING_TOKENS = 0
    week7_tools.VALIDATE_ARGS = True
    r = run_squad(a.question, inject_500=a.inject_500)
    print(json.dumps(r["output"], indent=2))


if __name__ == "__main__":
    main()
