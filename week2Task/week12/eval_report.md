# Eval report: the integrated SDK Docs Answer Engine

One command: `.venv/bin/python capstone.py eval` (it runs `week12_eval.py run` + `judge` on release r2). Every number
below comes from the stored runs in `week12/runs/*.jsonl`. The full terminal output for all four runs is
`eval_suite_output.md`; `capstone.py compare` reprints the headline table from the stored runs at no cost.

## 1. The number that moved

**Wrong-version code-sample rate**: answers with a code sample whose code fails the caller's version symbol table
(parse + imports resolve + every client method, keyword argument, exception and endpoint path exists in that version;
`week12_guards.check_code`, deterministic, no judge).

| Run | What changed | n (answers with code) | Wrong-version code | 95% CI (Wilson) |
|---|---|---|---|---|
| **r0_a** | Tuesday's wiring (Week 9 host, server and prompt) | 32 | **12 (37.5%)** | 22.9-54.7% |
| r1_a | version-aware prompt + Week 12 server | 19 | 1 (5.3%), and that one is C18 = redaction (mode 2) | 0.9-24.6% |
| r2_a | + host version pin, code check, notes, grounded citations | 19 | 1 (5.3%), again C18 = redaction | 0.9-24.6% |
| **r2_b** | + the closed-loop redaction fix | 19 | **0 (0.0%)** | 0.0-16.8% |

**37.5% → 0.0%** (12/32 → 0/19). For v2.4 callers alone: **11 of 14 → 0 of 6** answers with code were the wrong
version. The denominator shrank because r2 writes code for fewer answers: it declines where the caller's docs are
silent (C07, C08, C29, C30) and loses 4 answers to the spiral (mode 1). The two have to be read together. That is why
the outcome rate below is reported alongside.

Supporting numbers, same runs:

| | r0_a | r1_a | r2_a | r2_b |
|---|---|---|---|---|
| Outcome: all 12 assertions pass | 9/32 (28.1%) | 25/32 (78.1%) | 27/32 (84.4%) | **28/33 (84.8%)** |
| Gate: assertions AND judge PASS | 8/32 (25.0%) | - | - | **27/33 (81.8%)** |
| Samples that PARSE but fail the symbol table ("looks like code" goes red) | **10 of 30** | 0/18 | 0/18 | 0/19 |
| Trace id survives every MCP hop | 0/32 | 32/32 | 32/32 | **33/33** |
| Mean $/question | $0.00188 | $0.00290 | $0.00274 | $0.00314 |
| p50 latency | 16.1 s | 24.4 s | 21.8 s | 23.8 s |

**Bonus (stop judging code, execute the check).** 10 of r0's 30 parseable samples (33%) are red once "looks like
code" stops counting. The Week 6 bar (`code_parses`) passed all 10. judge_v2 PASSed 2 of r0's 12 wrong-version
answers: C10, where v3 `files.upload()` went to a 2.4 caller with the right "10 MB" fact, and C18, the redacted code
it is told not to grade. The parse + symbol-table check costs $0 and 0.2 ms; the judge costs one model call and still
missed both.

**What actually moved it (said plainly):** r0 → r1 did the work, through the prompt and the Week 12 server's tool
descriptions. r2's deterministic guards hardly fired with this model. Across r2_a and r2_b the host's version pin
rewrote 2 tool calls (C24, C30, both `2.9` → `3.0`), the code-check repair lap fired 0 times, and 0 citations were
dropped. The guards are what keep the number at 0 if the model or the prompt drifts. The unit tests prove they work
(`ThroughMcp.test_host_pins_retrieval_to_the_callers_version`,
`test_wrong_version_code_gets_one_repair_then_is_withheld`, with a fake model that writes v3 code for a 2.4 caller).
This live run does not.

## 2. The suite

33 cases (`eval_cases.jsonl`), written before any run, except C33, which was added from a failed trace (the closed
loop). 14 are v2.4 callers, 10 are v3 callers, 4 resolve the version from the question or a pasted snippet, 2 are
migrations, 2 ask about methods that exist in no version (`client.batch()`, `client.query()`), 2 are outside the docs
(GraphQL, "v4"), 2 carry pasted secrets, and C33 is the regression. 13 cases carry accepted tool paths for the
trajectory eval.

**Assertions before judges.** 12 deterministic assertions: `version_resolved`, `code_presence`, `code_parses`,
`code_runs_on_version` (the symbol table), `code_must_not`, `cites_version`, `citations_grounded`,
`deprecation_surfaced` (the symbol appears next to its 3.0 change), `removed_said_plainly`,
`answered_when_answerable`, `required_facts_present` and `pii_never_logged` (each pasted secret is absent from every
log file, host and MCP server). The judge keeps one criterion only, "directly answers".

**Pass rate per mode the case guards (r2_b):** W1 wrong-version 10/14 (all 4 fails are the spiral, none is wrong
code), W2 removed API plainly 6/7, W3 changed default 2/2, W4 invented symbol 2/2, W5 coverage 5/5, W7 secrets 2/2,
W8 redaction regression 1/1. The full per-mode and per-assertion tables for every run are in
`eval_suite_output.md`.

## 3. Judge agreement on the integrated system

judge_v2 (`week6/judge_v2.txt`, byte-identical to Week 6) was re-run on r2_b's integrated outputs. The question it
sees now carries the IDE's SDK version (seam S12). Labels were written blind from `labels/sheet_r2_b.md` (shuffled,
modes hidden) and locked (`labels/lock_r2_b.json`, sha256 + time) before the judge ran. `week12_eval.py judge`
refuses to run on an unlocked labelled run.

**Agreement: 31/33 = 93.9%** (clears 85%). Human PASS / judge PASS 27, human PASS / judge FAIL 2,
human FAIL / judge PASS 0, human FAIL / judge FAIL 4.

The two disagreements are both "judge stricter than the label", and both are honest partial answers (mode 7):
- C02: gives the documented v2 POST call and says truthfully that the v2 docs show no body parameter. The judge
  wanted a complete create-invoice call.
- C27: says `client.batch()` exists in no version and gives the one-request-per-call alternative. The judge read
  that as not answering "how do I use client.batch()".

**Which ones fail:** of the 6 judge FAILs, 4 are the spiral (C16, C21, C23, C24: "I don't know" with the answer
already in a tool result), and 2 are the honest declines above. One of them IS a breaking-change case: C16
(`client.upload_file()` raises AttributeError on 3.0). It failed by saying "I don't know" after `symbol_exists` had
already returned `files.upload`, not by inventing a signature. The other 6 removed/renamed-API cases (C12, C13, C14,
C15, C25, C26) were judged PASS. So the 18% the judge fails is concentrated in the spiral, and the breaking changes
are 1 of those 6, by refusal rather than by wrong code.

**Caveat that must be said:** the labels were written by Claude at the student's request, not by a human, exactly
as in Week 6 (`labels_r2_b.json` says so in its `labeler` field). To make the number a human-agreement number: edit
the labels, run `week12_eval.py lock-labels --run r2_b` after deleting `labels/lock_r2_b.json` and
`labels/judge_r2_b.json`, then run `week12_eval.py judge --run r2_b`. That costs 33 judge calls, about $0.02.

## 4. Trajectory eval (Week 8 method), 13 cases

See `trajectory.md`. Headline for r2_b: tool-choice accuracy **55/55 (100%)**, outcome 11/13 (84.6%), trajectory
(Week 8 strict, including laps ≤ 2x optimal) 6/13 (46.2%), **gap +38.5 points**. Evidence-only: 12/13 paths covered
(gap -7.7). Every strict failure is "too many laps" (5.15 taken vs 2.15 optimal), not a wrong tool.

## 5. What this suite does NOT cover

- **Whether the code runs.** The symbol table checks names, keyword arguments, imports, exceptions and endpoint
  paths. It does not check attributes on returned objects (`page.items`, `exc.retry_after_seconds`), argument
  types or values (`timeout_ms=120` vs `120000` passes), control flow, or that the call does what was asked. Nothing
  is executed against a real SDK, because none exists in this repo.
- **The Stack Overflow answers, the 200-sample `samples/` repo and the open-issues export** in the brief's corpus.
  This repo's corpus is 11 synthetic pages (4 v2, 7 v3), so the hostile question "what does dropping the SO answers
  cost your hit-rate?" cannot be answered here. There is no measurement either way.
- **Minor-version differences.** Docs exist per major only (v2 = 2.0-2.9). A method added in 2.6 would be served to
  a 2.4 caller.
- **Retrieval quality on its own.** No hit-rate@k on this run. Week 4's numbers are on the Week 4 golden set, not on
  these cases.
- **Variance.** Each release ran once (r2 twice). The spiral moved between cases from r2_a to r2_b (C05, C10 → C21,
  C24), so per-case results are not stable. Only the rates are.
- **Load, concurrency, and a real IDE client.** Every number is from 4 concurrent questions on one laptop.
- **Who the labeller is.** See section 3.
- **The judge runs saw two (fake) secrets.** Before seam S21 was fixed, the r0_a and r2_b judge prompts carried
  C31/C32's raw questions. The product never sent them to its model; the eval harness did. Fixed for every run after
  this one.
- **Multi-turn conversations and follow-ups.** Every case is one question.
