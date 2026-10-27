# Error taxonomy, re-scored on the INTEGRATED system (Week 5 method)

**What was scored:** every trace of four full eval runs through the single entry point: `r0_a` (Tuesday's wiring,
n=32), `r1_a` (prompt fix, n=32), `r2_a` (shipped, n=32) and `r2_b` (shipped + the closed-loop fix, n=33). Each mode
was found by reading traces, not from assertion names. The assertions were then used to *count* each mode across
every run. A trace can show more than one mode. Headline frequency = **r2_b** (what ships), with r0 for contrast.
The traces that were read in full are listed at the bottom.

## The modes

| # | Failure mode (what the integrator sees) | r0_a | r2_a | **r2_b (ships)** | Severity | Trace id | Origin |
|---|---|---|---|---|---|---|---|
| 1 | **Verification spiral, then "I don't know".** The agent keeps confirming names it already has (`Client`, `file_path`, `TooManyRequestsError.response`) with `symbol_exists` / `check_deprecation` until the 8-lap budget ends, then answers "I don't know" to a question the docs answer | 0/32 (0%) | 3/32 (9.4%) | **4/33 (12.1%)** | Dead end: the integrator gets nothing, and pays 1.7x ($0.0049 vs $0.0028 per passing answer) after 37 s | `tr-008ab778c2af` (r2_b C23) | **NEW: created by integration** |
| 2 | **Redaction-on-write corrupts the emitted code.** `WEBHOOK_SIGNING_SECRET = os.environ["..."]` becomes `[REDACTED:secret_assignment]"..."]` and stops parsing | 2/32 (6.3%) | 1/32 (3.1%) | **0/33 (0%)** after the fix (C33 guards it) | Ships broken code. No judge catches it: judge_v2 PASSed the r0 C18 answer | `tr-5871db30a290` (r0_a C18) | **NEW: created by integration** (closed loop) |
| 3 | **Wrong-version code sample.** A v2.4 caller gets v3 `list_after()` / `client.send()` / `timeout_ms`, which imports cleanly and fails at runtime | 12/32 (37.5%) | 1/19 with code* | **0/19 with code (0%)** | Ships code that passes review and fails in production: the brief's most expensive ticket | `tr-df2fb1813299` (r0_a C01) | Created by integration (seam S1: the Week 9 "answer with v3 code" prompt meets Week 11's v2 support) |
| 4 | **Trace id lost at the MCP hop.** Server-side work cannot be joined to the request | 32/32 (100%) | 0/32 | **0/33 (0%)** | Ops: an incident can't be traced past the agent | `tr-cd70c4189700` (r0 first run) | Created by integration (Week 9 server meets Week 11 tracing) |
| 5 | **Citation that names no version or was never retrieved** (spec paths, "check_deprecation: … returned not_in_changelog", `docs://openapi/...`) | 12/32 (37.5%) | 0/32 | **0/33 (0%)** | Misleads: the reader can't check the version the answer is for | `tr-79c0510dc95f` (r0_a C11) | Inherited (Week 7 contract allowed any string in `sources`) |
| 6 | **Code from the other version where the caller's docs are silent.** v2.4 asks to stream or verify a webhook and gets v3 `client.stream()` / `verify_signature` | 4/32 (12.5%) | 0/32 | **0/33 (0%)** | Ships code that does not exist on 2.4 | `tr-95dafe935473` (r0_a C07) | Inherited (Week 5 M2, "describes an API from the other version as current") |
| 7 | **Over-cautious decline on a partly documented question.** The documented call is given, but hedged as "can't give a verified way" (C02); a correct "doesn't exist" plus an alternative was judged not to answer (C27) | 0/32 | 1/32 (3.1%) | **1/33 (3.0%)** by assertion; the judge also FAILs C27 | Annoys: the developer has to read on | `tr-8c6660d5b357` (r2_b C02) | Created by integration: the side effect of the "never invent" rule that fixes mode 3 |

\* r2_a's single wrong-version answer is C18. That is mode 2 (the redaction corrupted the code), not the model
choosing v3. Counted once, under mode 2.

**Read-across (r2_b):** 5/33 traces show a mode (15%): 4 spirals plus C02. Both modes that ship broken code (2 and 3)
are at 0 in r2_b. On 19 answers with code, the 95% upper bound for mode 3 is still 16.8% (Wilson), so "0" means
"not seen in 19", not "solved".

## The modes integration created

Five of the seven modes (1, 2, 3, 4, 7) did not exist in any single week's part. Two of them have to be named for the
demo:

- **Mode 2 (redaction corrupts code)** is the cleanest example of an integration bug. Week 11's logger and Week 7's
  agent are both correct alone. The bug lives only where the redactor runs over the agent's output, so no unit test
  of either part could find it. It is the closed failure → test loop: found in `r0_a` C18, failing test written
  (eval case C33 + `test_redaction_never_corrupts_code_that_references_a_secret`), shown RED under policy v1, fixed
  (policy v2), GREEN in `r2_b` with no regression in the PII cases (C31, C32 still redact both secrets).
- **Mode 1 (verification spiral)** is the price of fixing mode 3. Adding `symbol_exists` plus the "never invent a
  signature" rule took wrong-version code from 37.5% to 0%. It also made the agent unable to stop checking. It is
  the top open mode and weakness #1, and it is NOT fixed (see `weaknesses.md`, `cost_and_10x.md`).

## Traces read in full (not just counted)

r0_a: `tr-df2fb1813299` (C01, v3 `list_after` to a 2.4 caller), `tr-5871db30a290` (C18, redacted code),
`tr-1a980ac2df98` (C08, v3 webhook code to 2.4 + redacted), `tr-db553d0fe8c6` (C28, client.query), `tr-40c3b9bd6183`
(C30, v4), `tr-c89c7150b24d` (C06), `tr-6109a0bbb0f1` (C09, v3 answer and v3 citation to 2.4), `tr-cd70c4189700`
(first r0 run, 0/2 server spans).
r2_a: `tr-fe662ce98d14` (C05 spiral, 8 laps on `TooManyRequestsError.response`), `tr-2ff1aa0adc73` (C10 spiral,
checks `file_path` and `Client` in the changelog), `tr-940a68239c72` (C23 spiral), `tr-2bf4e9665c5d` (C02 hedge),
`tr-c833c39bdbd6` (C18 redacted again).
r2_b: `tr-c6f5ad30e6f6` (C16 spiral: had `files.upload` from `symbol_exists` in lap 2, still said "I don't know"),
`tr-008ab778c2af` (C23 spiral: had `page_size` in lap 1), plus every answer in `labels/sheet_r2_b.md` while labelling.
