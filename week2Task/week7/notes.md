# Week 7 Task Set E: racing the docs agent against a fixed workflow

**Task:** answer a migration question with v3 code. That means finding the docs page, reading the OpenAPI spec, checking the changelog for deprecations, and writing the v3 sample.

**Output contract (same for both systems):** `{answer, v3_code, deprecations[], sources[]}`.

**Model (same for both):** Claude Haiku 4.5 through the headless `claude` CLI.

**Tools (same for both):** `search_docs`, `get_openapi_spec`, `check_deprecation`, all in `week7_tools.py`.

| Command | What it runs |
|---|---|
| `.venv/bin/python week7_agent.py --qid Q01` | the agent: plan → act → observe loop, 4 budgets (`week7_agent.py`) |
| `.venv/bin/python week7_workflow.py --qid Q01` | the fixed workflow: 5 hard-coded steps, no loop (`week7_workflow.py`) |
| `.venv/bin/python week7_race.py [--no-thinking]` | the race: 10 questions × 3 repeats × 2 systems → `race*.csv` |
| `.venv/bin/python -m unittest tests.test_week7_budgets` | each of the 4 budgets stops a spinning agent (fake LLM, no cost) |

## 1. Third tool: `check_deprecation`

`tool_descriptions.diff` shows the change.
- The two existing descriptions overlapped: both claimed "endpoints" and "parameters".
- They were sharpened so each names **one job** and says what it does *not* do.
- The third tool looks up **one symbol** in the changelog, with `api_version` as an enum `["v2","v3"]`. `search_docs.api_version` also became an enum.
- No two descriptions claim the same job: prose search, schema by exact path, and changelog status by symbol.

The data comes from `week7/changelog_v3.json`, whose entries are taken verbatim from the corpus. `upload_file` is deliberately missing, because the real changelog never mentions it (Q05 tests that). `week7/openapi_v3.json` was written for this week, since no spec ships with the corpus; everything in it except the `list_after()` page shape comes from the v3 docs.

## 2. The workflow is the same task with no loop

Every run executes the same fixed steps:
1. An LLM call extracts `{symbol, path, search_query}`.
2. `search_docs(query, "v3")`.
3. `check_deprecation(symbol, "v3")`.
4. `get_openapi_spec(path)`. The path is the `replacement_path` from step 3, or else the question's path with `/v2/` changed to `/v3/`.
5. An LLM call writes the contract.

Each step runs at most once, and steps 3 and 4 are skipped when their input is null. There's no loop, retry or model-chosen next step. Both systems use the same tool functions, `CONTRACT`, `parse_contract` and grader.

## 3. The race: 10 questions, 3 repeats each

`week7/questions.jsonl` has 10 questions in two groups:
- **Dependent (6), where step 3 depends on what step 2 found.** Q01 (`client.request` removed → `Client.send` → POST spec), Q02 (`paginate_auto` removed → `list_after` → GET spec), Q03 (`TooManyRequestsError` renamed), Q04 (`timeout_s` renamed and the unit changes), Q05 (`upload_file` isn't in the changelog, so the docs must be searched) and Q06 (the default changed).
- **Single lookups (4).** Q07–Q10.

The grader is deterministic: the code must parse; required v3 symbols must appear; v2 symbols must not appear; and the deprecations list must name the changed symbols. Tokens are **summed across every lap**, including tokens the agent re-sends each lap.

### Headline table (`race_no_thinking.csv`; extended thinking off for both systems)

| | Pass rate | p50 latency | Total tokens (10 q) | Cost / question |
|---|---|---|---|---|
| **Agent** | 90% (27/30) | 11.6 s | 56,715 | $0.0085 |
| **Workflow** | **97% (29/30)** | **5.6 s** | **16,720** | **$0.0026** |

### First race, CLI default settings with thinking on (`race.csv`)

| | Pass rate | p50 latency | Total tokens (10 q) | Cost / question |
|---|---|---|---|---|
| Agent | 97% (29/30) | 13.0 s | 57,594 | $0.0102 |
| Workflow | 93% (28/30) | 16.2 s | 31,430 | $0.0097 |

**Why there are two tables (in order of what happened):**
- The default race ran first. There, the agent led on pass rate (by one run in 30) and on p50 latency.
- Timing each step showed why: the workflow's step 1, a 50-token JSON extraction, spent **455–1,404 output tokens and 5–13 s on hidden thinking**.
- Thinking is a model setting, so I re-ran the whole race with it off for **both** systems. That step then drops to 40 tokens and 1 s.
- The headline table is the setting I'd ship for this task. The first table stays here because it's what was measured first.

**Failures, all read from the logs:**
- **Workflow (3 runs):** Q03 twice under default thinking (a `try:` block whose body is only a comment, so it doesn't parse), and Q10 once (it never used `retry_after_seconds`).
- **Agent (4 runs):** each started by breaking its own reply protocol, for example wrapping the call in `<function_calls>[…]` or starting to chat ("I'm ready, please ask…"). After the error message it answered **without calling tools** and invented APIs: `client.invoices.create`, hand-rolled HMAC code, and empty code after 6 laps.
- **Agent protocol breaks overall:** replies that were neither a tool call nor a final answer happened 5 times (thinking on) and 25 times (thinking off) across 30 runs each (`agent_tool_usage.txt`).

## 4. Budgets: all four enforced, and a clean termination

`Budgets(max_iters=8, max_tokens=60_000, max_cost_usd=0.05, max_wall_s=120)`. Before every lap, the loop refuses to start a lap that would cross the token, cost or wall-clock budget, estimating the lap from the prompt size and the last lap's cost. After every lap it re-checks the actual totals. The LLM call also gets the remaining wall-clock time as its timeout. `tests/test_week7_budgets.py` shows each budget stopping a fake agent that never finishes.

Real run: `week7_agent.py --qid Q02 --max-tokens 6000`, in `budget_termination.log` and `.jsonl`.

```
lap 1 check_deprecation(paginate_auto, v3) -> removed, use list_after()   tokens_total 1447
lap 2 search_docs("...list_after...", v3)                                  tokens_total 3033
lap 3 search_docs(again, a rephrased query)                                tokens_total 4994
{"event": "end", "status": "budget_exceeded", "budget": "max_tokens",
 "detail": "4994 used + ~1642 for lap 4 > 6000", "llm_calls": 3, "cost_usd": 0.0078}
```

It stops before paying for lap 4, returns no half-built answer, and the log names the budget that fired. The log also shows a small search thrash (two `search_docs` calls in a row), which is exactly what the budget exists for.

## 5. Verdict (under 150 words)

The decision rule asks whether the path varies by input. On these 10 questions it doesn't. All six dependent questions follow the same shape: extract the symbol, check deprecation, look up the replacement's spec or docs, then write. Even Q05, where the changelog is silent, is solved by the workflow's always-on docs search (3/3 in both races).

The agent's paths did vary: 11 distinct tool sequences per race. But that variation was noise, not the input. The same question took different paths across repeats, and 3 runs skipped the tools entirely.

With thinking off, the workflow wins all four numbers: 97% vs 90%, 5.6 s vs 11.6 s, 3.4× fewer tokens and 3.3× cheaper. With default thinking the agent led on pass rate by one run in 30 and on latency, but still used 1.8× the tokens.

**None of the 10 questions needs an agent. Ship the workflow.**

---

**Caveats:**
- Latency includes about 0.3 s of `claude` CLI start-up per call, which penalises the agent's extra calls slightly.
- There are 3 repeats per question, so a 1-in-30 pass-rate gap is within noise.
- The "before" two-tool loop was never raced. The diff documents the description change, not a measured thrash reduction.
