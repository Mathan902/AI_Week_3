# Failure case: version/deprecation worker returns HTTP 500

**Behaviour:** the orchestrator **did not retry**. It **degraded to a partial answer**: in 3/3 runs it said the version check failed, and it still shipped a code sample that had no version check behind it.

**Command:** `.venv/bin/python week10_race.py failure --case E09 --repeats 3`. Raw runs are in `failure_runs.jsonl`, terminal output in `failure_stdout.txt`, and event logs in `logs/squad_E09_r{1,2,3}_500.jsonl`.

**Case:** E09, *"TooManyRequestsError how to get the retry delay"*. It's one of the 10 race cases. I picked it because it is the race case whose right answer depends most on the version check: `TooManyRequestsError` is a v2 name, renamed to `RateLimitError` in v3.

**Injection:** `run_squad(..., inject_500=True)` replaces the version worker's hop with `{"status": 500, "error": "HTTP 500 Internal Server Error from version/deprecation worker"}`. No model call is made for that hop. `handoffs.log`-style records show it as `orchestrator -> version worker lap 0, 0 tokens, ERROR: HTTP 500`.

## What the orchestrator actually did

The orchestrator has no retry and no failure policy. It passes the error JSON unchanged to the code-sample worker as `VERSION FINDINGS` and to the synthesis call. Everything after that is what the model decided:

| Run | Retried? | Said the check failed? | Shipped code anyway? | Where the v2→v3 rename came from | Week-6 result |
|---|---|---|---|---|---|
| r1 | no | yes: *"The version/deprecation check failed, so I could not confirm whether `TooManyRequestsError` was renamed"* | yes, `from acme import RateLimitError  # import path assumed` | the code worker's own v3 docs search (`v3-errors::ratelimiterror::2`) | **PASS** |
| r2 | no | yes: *"the rename rests on the code-sample worker's report alone"* | yes, with `RateLimitError` used but never imported | code worker's v3 docs | FAIL (`deprecation_has_migration_note`; judge PASS) |
| r3 | no | yes: *"the v2-to-v3 rename is based only on the v3 docs"* | yes, a bare `except RateLimitError: raise` that never reads the delay | code worker's v3 docs | FAIL (assertion and judge) |

**Compared with the same case with no injection (race runs):**

| | Pass | Mean tokens | Mean latency |
|---|---|---|---|
| Squad, version worker healthy | 2/3 | 20,907 | 42.3 s |
| Squad, version worker returns 500 | 1/3 | 11,192 | 28.8 s |
| Single agent | 3/3 | 13,678 | 21.5 s |

**Why it isn't a lie, and why it's still a problem:**
- It isn't a lie, because all three answers disclose the missing check.
- It's still a problem, because the sample ships anyway. One run imports from a path the model says it "assumed", one doesn't import at all, and one doesn't answer the question.
- A developer who skims past the caveat gets unchecked code.

**Second finding:** losing the version worker made the squad **cheaper and faster**, with no clear loss in quality. The code worker's v3 docs search already found the rename. That matches the race result: the version worker is the hand-off that costs the most and contributes the least (see `notes.md` §3).
