"""Week 7: the hand-built docs agent. Plan -> act -> observe, every lap logged, four budgets enforced.

    .venv/bin/python week7_agent.py "How do I migrate client.request(...) to v3?"
    .venv/bin/python week7_agent.py --qid Q01                      # a question from week7/questions.jsonl
    .venv/bin/python week7_agent.py --qid Q01 --max-tokens 6000    # tighten any budget to watch it fire

Each lap re-sends the whole message list, so the tokens and cost of EVERY lap are summed. The last
call alone understates the agent by a multiple.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from week7_tools import CONTRACT, TOOLS, W7, LLMError, call_llm, parse_contract, run_tool


@dataclass(frozen=True)
class Budgets:
    max_iters: int = 8
    max_tokens: int = 60_000
    max_cost_usd: float = 0.05
    max_wall_s: float = 120.0


SYSTEM = f"""You are a migration agent for the Acme Python SDK. Developers bring v2 code or v3 questions; you answer with v3 code.
You work in steps. Each reply is exactly ONE JSON object and nothing else:
  {{"thought": "<why>", "tool": "<tool name>", "args": {{...}}}}   to call one tool, or
  {{"thought": "<why>", "final": <output contract>}}                 when you are done.
Tools:
{json.dumps(TOOLS, indent=1)}
Output contract for "final":
{CONTRACT}"""


def render(question: str, steps: list[dict]) -> str:
    lines = [f"QUESTION:\n{question}\n"]
    for s in steps:
        lines.append(f"YOU:\n{s['reply']}\nTOOL RESULT:\n{json.dumps(s['result'])[:3000]}\n")
    lines.append("Reply with the next JSON object.")
    return "\n".join(lines)


def _parse_action(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def run_agent(question: str, budgets: Budgets = Budgets(), llm=call_llm, log_path: Path | None = None,
              echo: bool = True) -> dict:
    t0 = time.perf_counter()
    steps: list[dict] = []
    totals = {"llm_calls": 0, "tokens": 0, "cost_usd": 0.0}
    log = []

    def emit(event: dict) -> None:
        event = {"t": round(time.perf_counter() - t0, 2), **event}
        log.append(event)
        if echo:
            print(json.dumps(event))

    def finish(status: str, output: dict | None = None, **extra) -> dict:
        result = {"system": "agent", "status": status, "output": output, "laps": totals["llm_calls"],
                  "latency_s": round(time.perf_counter() - t0, 2), **totals, **extra}
        emit({"event": "end", **{k: v for k, v in result.items() if k != "output"}})
        if log_path:
            log_path.write_text("\n".join(json.dumps(e) for e in log) + "\n")
        return result

    emit({"event": "start", "question": question, "budgets": budgets.__dict__})
    last_lap_tokens = last_lap_cost = 0.0
    for lap in range(1, budgets.max_iters + 1):
        prompt = render(question, steps)
        elapsed = time.perf_counter() - t0
        # Pre-lap checks: refuse a lap that would cross a budget, estimating it from the prompt size
        # (about 4 chars per token) and the last lap's cost, instead of finding out after paying for it.
        est_tokens = (len(SYSTEM) + len(prompt)) // 4 + 300
        est_cost = last_lap_cost * est_tokens / last_lap_tokens if last_lap_tokens else 0.0
        if elapsed >= budgets.max_wall_s:
            return finish("budget_exceeded", budget="max_wall_s", detail=f"{elapsed:.1f}s >= {budgets.max_wall_s}s")
        if totals["tokens"] + est_tokens > budgets.max_tokens:
            return finish("budget_exceeded", budget="max_tokens",
                          detail=f"{totals['tokens']} used + ~{est_tokens} for lap {lap} > {budgets.max_tokens}")
        if totals["cost_usd"] + est_cost > budgets.max_cost_usd:
            return finish("budget_exceeded", budget="max_cost_usd",
                          detail=f"${totals['cost_usd']:.4f} + ~${est_cost:.4f} for lap {lap} > ${budgets.max_cost_usd}")
        try:
            resp = llm(SYSTEM, prompt, timeout_s=budgets.max_wall_s - elapsed)
        except TimeoutError as exc:
            return finish("budget_exceeded", budget="max_wall_s", detail=str(exc))
        except LLMError as exc:
            return finish("error", detail=str(exc))
        totals["llm_calls"] += 1
        totals["tokens"] += resp["tokens"]
        totals["cost_usd"] += resp["cost_usd"]
        last_lap_tokens, last_lap_cost = resp["tokens"], resp["cost_usd"]
        action = _parse_action(resp["text"]) or {}
        if "tool" not in action and "final" not in action and parse_contract(json.dumps(action)):
            action = {"thought": "(bare output contract, accepted as final)", "final": action}
        emit({"event": "lap", "lap": lap, "tokens_lap": resp["tokens"], "tokens_total": totals["tokens"],
              "cost_total": round(totals["cost_usd"], 5), "thought": action.get("thought", "")[:160],
              "tool": action.get("tool"), "args": action.get("args"), "final": "final" in action,
              **({} if action.get("tool") or "final" in action else {"unparsed_reply": resp["text"][:300]})})
        # Post-lap checks: a lap that turned out bigger than estimated still stops the run.
        if totals["tokens"] > budgets.max_tokens:
            return finish("budget_exceeded", budget="max_tokens", detail=f"{totals['tokens']} > {budgets.max_tokens}")
        if totals["cost_usd"] > budgets.max_cost_usd:
            return finish("budget_exceeded", budget="max_cost_usd",
                          detail=f"${totals['cost_usd']:.4f} > ${budgets.max_cost_usd}")
        if "final" in action:
            output = parse_contract(json.dumps(action["final"])) if isinstance(action["final"], dict) else None
            return finish("done" if output else "bad_final", output)
        if action.get("tool"):
            result = run_tool(action["tool"], action.get("args") or {})
        else:
            result = {"error": "reply was not one JSON object with 'tool' or 'final'"}
        emit({"event": "tool_result", "lap": lap, "tool": action.get("tool"), "result": json.dumps(result)[:200]})
        steps.append({"reply": resp["text"].strip(), "result": result})
    return finish("budget_exceeded", budget="max_iters", detail=f"{budgets.max_iters} laps without a final answer")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="?")
    p.add_argument("--qid")
    p.add_argument("--max-iters", type=int, default=Budgets.max_iters)
    p.add_argument("--max-tokens", type=int, default=Budgets.max_tokens)
    p.add_argument("--max-cost", type=float, default=Budgets.max_cost_usd)
    p.add_argument("--max-wall", type=float, default=Budgets.max_wall_s)
    p.add_argument("--log")
    a = p.parse_args()
    question = a.question
    if a.qid:
        qs = {q["id"]: q for q in map(json.loads, (W7 / "questions.jsonl").read_text().splitlines())}
        question = qs[a.qid]["question"]
    budgets = Budgets(a.max_iters, a.max_tokens, a.max_cost, a.max_wall)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = Path(a.log) if a.log else W7 / "logs" / f"agent_{a.qid or 'adhoc'}_{stamp}.jsonl"
    result = run_agent(question, budgets, log_path=log)
    print(json.dumps(result.get("output"), indent=2))
    print(f"log: {log}")


if __name__ == "__main__":
    main()
