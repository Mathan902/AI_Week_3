# Week 10 race: docs squad vs single agent

Same 10 Week-6 cases for both arms (`week6/eval_set.jsonl`, selection in `week10/cases.json`), 3 repeats each, model `haiku` (thinking off), judge `judge_v2` + 8 Week-6 assertions. A run passes only if no assertion fails and the judge says PASS.

| Arm | Pass rate | p50 latency | p99 latency | Total tokens (10 cases) | Cost / question |
|---|---|---|---|---|---|
| Single agent (`week7_agent.py`) | 23/30 (77%) | 16.9 s | 39.5 s | 117,861 | $0.0021 |
| Squad (`week10_squad.py`) | 21/30 (70%) | 43.1 s | 71.7 s | 197,488 | $0.0042 |

**Context re-send multiplier: squad 197,488 / single 117,861 tokens = 1.7x. Largest share: "orchestrator -> version worker" (119 calls), 47% of all squad tokens.**

Total tokens is one pass over the 10 cases (sum over all runs / repeats). p99 is nearest-rank over 30 runs per arm, so it is the slowest run.

## Supporting numbers

| Arm | Assertions pass | Judge PASS | Tokens / question | LLM calls / question |
|---|---|---|---|---|
| single | 23/30 | 26/30 | 11,786 | 4.0 |
| squad | 22/30 | 27/30 | 19,749 | 9.0 |

## Per case (passes out of repeats)

| Case | Mode | Question | Single | Squad |
|---|---|---|---|---|
| E01 | M1 | what scheme does verify_signature expect | 3/3 | 2/3 |
| E05 | M1 | hw to verify webhok signature | 3/3 | 1/3 |
| E09 | M2 | TooManyRequestsError how to get the retry delay | 3/3 | 2/3 |
| E10 | M2 | does the sdk automatically retry 429s | 3/3 | 2/3 |
| E11 | M3 | what is part_size_mb | 1/3 | 1/3 |
| E14 | M3 | what is retry_backoff_ms | 1/3 | 2/3 |
| E18 | M4 | how do I authenticate the client? | 3/3 | 3/3 |
| E19 | M4 | how many failures before my webhook is turned off | 3/3 | 3/3 |
| E21 | M5 | list of removed apis in v3 | 0/3 | 2/3 |
| E25 | M6 | is the client thread safe | 3/3 | 3/3 |

## Why runs failed (first failing check per run)

- single E11 r1: code_parses: fenced code is on a single line
- single E11 r3: code_parses: fenced code is on a single line
- single E14 r2: answered_when_answerable: refused an answerable question; required_facts_present: refused (judge also FAIL)
- single E14 r3: answered_when_answerable: refused an answerable question; required_facts_present: refused (judge also FAIL)
- single E21 r1: answered_when_answerable: refused an answerable question; required_facts_present: refused (judge also FAIL)
- single E21 r2: answered_when_answerable: refused an answerable question; required_facts_present: refused (judge also FAIL)
- single E21 r3: answered_when_answerable: refused an answerable question; required_facts_present: refused
- squad E01 r2: no_repeated_sentence: repeats: 'over the raw request body keyed with the...'
- squad E05 r1: cites_question_version: cites nothing, question is v3; required_facts_present: missing /verify_signature/ (judge also FAIL)
- squad E05 r3: cites_question_version: cites nothing, question is v3; required_facts_present: missing /verify_signature/ (judge also FAIL)
- squad E09 r1: deprecation_has_migration_note: ['TooManyRequestsError'] with no migration note (use RateLimitError)
- squad E10 r2: no_repeated_sentence: repeats: 'send v3 invoices print resp except ratelimiterror as...'
- squad E11 r2: no_repeated_sentence: repeats: 'of each multipart chunk used for large uploads...'
- squad E11 r3: no_repeated_sentence: repeats: 'the size of each multipart chunk in megabytes...'
- squad E14 r3: no_repeated_sentence: repeats: 'default changed from 2000 ms in v2 to...'
- squad E21 r1: judge FAIL: The answer correctly names `paginate_auto()` as removed, but its claim that `Client.request()` was removed and replaced by `Client.send()` appears nowhere in the shown documentation, so the list is not correct according to the docs.
