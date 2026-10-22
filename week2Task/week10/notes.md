# Week 10 Task Set E: docs squad vs single agent

**Single agent:** `week7_agent.py`, the Week 7 plan→act→observe loop.
- 3 tools, 8-lap budget.
- Week 8 argument validation on.

**Squad:** `week10_squad.py`.
- **Orchestrator:** a plan call, then a synthesis call.
- **Version/deprecation worker:** tools `check_deprecation` and `search_docs`, 4-lap cap, no code.
- **Code-sample worker:** tools `search_docs` and `get_openapi_spec`, 4-lap cap.
- Each worker gets a **brief**, not the transcript. The code worker's brief carries the target version and the version findings, so it can't silently fall back to v2 (`tests/test_week10_squad.py` asserts this).

**Shared by both arms:**
- Model: `haiku` through the `claude` CLI, which now resolves to `claude-haiku-5-5`.
- Extended thinking off.
- The same tool functions and output contract.
- One renderer from the contract to Week-6 answer text (`render_answer`).

**Judge:** the Week-6 `judge_v2` prompt (unchanged) plus the 8 Week-6 assertions. A run passes only if both pass.

| Command | What |
|---|---|
| `.venv/bin/python week10_race.py select` | picks the 10 cases once and records the eval_set sha256 (`cases.json`) |
| `.venv/bin/python week10_race.py run` | 10 cases × 3 repeats × 2 arms, shuffled, 3 at a time, then the judge → `runs.jsonl`, `race_table.md`, `handoffs.log`, `multiplier.txt` |
| `.venv/bin/python week10_race.py report` | rebuilds the three reports from `runs.jsonl` |
| `.venv/bin/python week10_race.py failure --case E09` | version worker → HTTP 500 → `failure_runs.jsonl` |
| `.venv/bin/python -m unittest tests.test_week10_squad` | hand-off logging, target version in the brief, injected 500 path (fake LLM, no cost) |

## 1. Same cases, same ruler

**Which cases:**
- Week 6 has 25 cases. The 10 used here were picked by `select` *before any run*.
- The pick is stratified by Week-5 mode (2/2/2/2/1/1), using `random.Random(10)` within each mode.
- The result is **E01 E05 E09 E10 E11 E14 E18 E19 E21 E25**.
- No case was written or edited. `run` refuses to start if `week6/eval_set.jsonl` changed since the pick.

**Judge context:** each run's "documentation shown" is every chunk, changelog entry and spec entry that the run's tools returned. The prompt header still says "top 3", because the prompt is left byte-identical.

**Caveat:** the `haiku` alias now resolves to Haiku 5.5, while Week 6 measured Haiku 4.5. It is the same judge for both arms, but it is not the same judge as Week 6.

## 2. Race table

See `race_table.md`, which also has per-case results and the first failing check of every failed run.

| Arm | Pass rate | p50 | p99 | Total tokens (10 cases) | Cost / question |
|---|---|---|---|---|---|
| Single agent | **23/30 (77%)** | **16.9 s** | **39.5 s** | **117,861** | **$0.0021** |
| Squad | 21/30 (70%) | 43.1 s | 71.7 s | 197,488 | $0.0042 |

**How to read the numbers:**
- **Pass rate:** the 2-run gap is within noise. The judge alone even prefers the squad slightly (27/30 vs 26/30).
- **Where the squad loses passes:** to assertions, mostly `no_repeated_sentence` (5 runs). The synthesis restates a worker's fact in the answer text and again in a code comment.
- **Where the single agent loses passes:**
  - 5 budget exits. E14 twice and E21 three times hit the 8-lap budget with no answer, which renders as "I don't know".
  - Two one-line code fences on E11.
- **Latency and cost:** these aren't close. The squad is 2.5× slower at p50 and costs 2.0× per question.

## 3. Context re-send multiplier

> **Context re-send multiplier: squad 197,488 / single 117,861 tokens = 1.7×. Largest share: "orchestrator -> version worker" (119 calls), 47% of all squad tokens.**

| Hand-off (`handoffs.log`, 30 squad runs) | Calls | Tokens | Share |
|---|---|---|---|
| orchestrator → version worker | 119 | 277,047 | **46.8%** |
| orchestrator → code-sample worker | 90 | 218,497 | 36.9% |
| workers → orchestrator (synthesis) | 30 | 66,759 | 11.3% |
| user → orchestrator (plan) | 30 | 30,161 | 5.1% |

**Why the version worker dominates:** it re-sends its brief plus its own growing history every lap. Lap 1 averages 1,595 tokens and lap 4 averages 3,117. It reached lap 4 in 29/30 runs and **hit the cap with no final in 24/30**.
- The logs show the cause. For questions with no version angle (E19 "how many failures before my webhook is turned off", E25 "is the client thread safe"), the orchestrator's plan still asks it to establish "whether this differs between v2 and v3".
- So it runs `search_docs` against v3, then v2, then v3 again, and never concludes.
- The code worker then answers from its own search, so **47% of the bill buys, in most runs, an `{"error": "no final after 4 laps"}`.**

**Fixed per-call tax:** a trivial `claude -p` call bills about 576 input tokens. The squad makes 9.0 calls per question against the single agent's 4.0. That fixed overhead is 26% of squad tokens (269 × 576) and 20% of single-agent tokens. More hops cost more even before any context is re-sent.

**What I did not do:** I did not fix the version worker's brief and re-run the squad. That would be re-running the multi arm until it wins, and it would test the brief rather than the pattern. The fix is written down as the first thing to try if this is ever re-raced: scope `version_task` to the symbols only, and skip the worker when `symbols` is empty.

## 4. Injected 500

See `failure_case.md`. The orchestrator didn't retry. It **degraded**, shipping a sample in 3/3 runs while saying the version check had failed. Pass rate on E09 went from 2/3 to 1/3. Tokens *dropped* from 20.9k to 11.2k, and latency from 42 s to 29 s.

## 5. Verdict

**KILL.** See `verdict.md` (10 lines, sunk-cost named first).

**When multi-agent would be worth it:** when the sub-tasks are independent and can run in parallel, or need genuinely different instructions or permissions. Neither holds here: the code sample needs the version answer first, and both workers search the same docs.

## Bonus: AgentCard and the A2A lifecycle

**AgentCard:** `agent_card.json`.
- 2 skills.
- Input `text/plain`, output `application/json` and `text/plain`.
- OAuth2 client-credentials auth with a `docs:read` scope.
- `stateTransitionHistory` on, so a caller can see a task go `working → input-required`.

**Mapping the E09 500 onto the task lifecycle.** The task should **not** end `completed` with an unchecked sample, which is what it did. It also shouldn't end `failed`, because nothing about the question is unanswerable. The version is the one fact that would let the squad answer without the worker:
- E09 names a v2 symbol (`TooManyRequestsError`), so the developer's version is genuinely ambiguous. The Week 6 notes found the same ambiguity on E09 and E07.
- So the task should move `working → input-required` with *"Which acme-sdk version are you on, v2 or v3?"*
- The caller's reply resumes the same `taskId` and `contextId`. With "v2" the answer is `exc.response.headers["Retry-After"]`; with "v3" it's `RateLimitError.retry_after_seconds`.
- The task should end `failed` only if the worker is still down after one retry *and* the version is still unknown.

**What A2A buys over a plain REST call to the worker:**
- A shared task lifecycle (`submitted / working / input-required / completed / failed`), so "I need the SDK version" is a standard state the caller already understands, not an HTTP 500 or a free-text caveat inside a 200.
- A discoverable AgentCard (skills, modes, auth), so a caller can find and authorize the agent without reading its code.
