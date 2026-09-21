# Week 6 Task Set E: validating the docs-answer judge

The system under test is unchanged from Week 5 (commit `51025901`): the baseline retriever feeds the extractive generator. No `.py` file of the pipeline was touched this week. Everything new is `week6_eval.py`, `week6/` and `tests/test_week6_assertions.py`.

**One command:** `.venv/bin/python week6_eval.py`. It asks the pipeline all 25 questions, runs 8 assertions, runs the judge (only once the labels are locked) and prints the pass rate by mode, plus judge-vs-human agreement.

---

## 1. Eval set: 25 cases, each tagged with one Week-5 mode

`week6/eval_set.jsonl`. Every question is taken verbatim from a real trace, and the eval checks this.

| Mode (Week 5 taxonomy) | Cases |
|---|---|
| M1 Code sample squashed onto one line or cut off mid-call | E01–E05 |
| M2 Describes a v2-only API as current, no "removed in v3" warning | E06–E10 |
| M3 Quotes the sentence next to the fact instead of the fact | E11–E14 |
| M4 Says "I don't know" while a top-3 chunk states the answer | E15–E19 |
| M5 Fetches chunks about a different topic, then says "I don't know" | E20–E22 |
| M6 Prints the same sentence twice in one answer | E23–E25 |

**Regression cases: 16.** 15 of them are the failed traces from the Week 5 seeded sample (for example `tr-16c2469574`, `tr-16cdcfb0f1` and `tr-4fc7b3e2f0`), and E18 is the failed demo trace `tr-b52c17cd99`. Each is replayed with its question verbatim. The eval prints `Regression replay: 16/16 answers byte-identical to the original failed trace's raw_output`, which shows the failures still reproduce.

## 2. Assertion / judge split: 8 assertions vs 1 judged criterion

The judge prompt before the split (`judge_v0_pre_split.txt`, kept for reference and never run) scored helpfulness from 1 to 10 across 6 mixed criteria. Five of those can be checked by a parser or a lookup. They moved into code and were **deleted from the judge prompt**:

| Criterion removed from the judge | Assertion in `week6_eval.py` | How it's checked |
|---|---|---|
| Code sample parses | `code_parses` | `ast.parse` on each fenced block. It fails on unfenced code and on one-line fences. |
| Endpoint path exists | `endpoints_in_spec` | Every `/vN/...` path must be in `week6/openapi_v3.json`. |
| API version is stated | `version_stated` | The answer text, not just the citation, must say the version(s) the case needs. |
| Deprecated symbol has a migration note | `deprecation_has_migration_note` | Any symbol from `week6/deprecations.json` needs "removed / renamed / instead / …". |
| No duplicated sentences | `no_repeated_sentence` | No repeated sentence and no repeated 8-word run. |

There are also 3 assertions that no judge criterion covered: `cites_question_version`, `answered_when_answerable` and `required_facts_present`.
**Count: 8 deterministic assertions, 1 judged criterion** (DIRECTLY ANSWERS, binary PASS/FAIL, in `judge_v1.txt`).
The assertions have unit tests (`tests/test_week6_assertions.py`, 7 tests) that show they pass on good answers and fail on the mangled ones.

*Caveat:* no OpenAPI document ships with this corpus. `openapi_v3.json` contains exactly the paths the v3 docs use (`/v3/invoices` and `/v3/events`). `/v2/` paths are left out on purpose, because the assistant ships to v3 users.

### Eval table (assertions only, before any judge run)

From `week6/eval_table_before_judge.txt`:

```
M1  Code sample squashed / cut off                  5   0/5 (0%)
M2  v2-only API as current, no removal warning      5   0/5 (0%)
M3  Quotes the sentence next to the fact            4   0/4 (0%)
M4  "I don't know" while top-3 has the answer       5   0/5 (0%)
M5  Different-topic chunks, then "I don't know"     3   0/3 (0%)
M6  Same sentence printed twice                     3   0/3 (0%)
all                                                25   0/25 (0%)
```

All 25 fail at least one assertion. That's expected: every case was built from a real failure, and nothing has been fixed. The table is the baseline the Week 5 prediction (`week5/prediction.md`) will be measured against.

## 3. Blind protocol: labels before the judge

> **Who labelled.** The student asked Claude Opus 5 to write the 25 labels, so the "human" labels here are **not human**. Agreement below measures Claude Opus 5 against Claude Haiku 4.5, not a person against the judge. The `labeler` field in `labels_25.json` says so. To make this a true human validation, a person relabels from `labeling_sheet.md` and the same commands are re-run.

1. `week6_eval.py sheet` wrote `labeling_sheet.md`. It holds the 25 answers in a shuffled order, with no mode tags and no judge output, because none existed yet.
2. All 25 were labelled in `labels_25.json` against the exact criterion text the judge gets, each with a one-line reason: **8 PASS, 17 FAIL**.
3. `week6_eval.py lock-labels` wrote `labels_lock.json`, with the labels' sha256, the lock time and a hash of the 25 answers labelled.
4. The judge refuses to run if the lock is missing, if the labels changed after locking, or if the answers differ from the labelled ones. `judge_v2` also refuses without `prediction.txt`.

**Ordering evidence (all UTC, 2026-09-21):**

| Event | Time | Where it is recorded |
|---|---|---|
| labels_25.json last written | 16:00:33 | `labels_lock.json` → `labels_mtime_utc` |
| labels locked | 16:00:43 | `labels_lock.json` → `locked_at_utc` |
| **labels committed** | **16:00:52** | commit **`8edb336e`**, which contains only `labels_25.json` and `labels_lock.json` |
| judge_v1 run started | 16:01:04 | `judge_runs/judge_v1.json` → `started_at_utc` |
| prediction.txt written | 16:03:01 | `judge_runs/judge_v2.json` → `prediction_mtime_utc` |
| judge_v2 run started | 16:03:28 | `judge_runs/judge_v2.json` → `started_at_utc` |

## 4. Agreement

The judge is Claude Haiku 4.5 (`claude-haiku-4-5-20251001`), called headless through `claude -p --model haiku` with no tools, no MCP and no project settings. The only criterion is DIRECTLY ANSWERS, binary.

| | Recorded run (`judge_runs/`) | Mean of 4 runs (recorded + 3 reruns, `judge_runs/stability_3x.json`) |
|---|---|---|
| **agreement_before** (judge_v1) | **22/25 = 88%** | 22.5/25 = 90% (runs: 22, 23, 24, 21) |
| **agreement_after** (judge_v2) | **25/25 = 100%** | 24.25/25 = 97% (runs: 25, 24, 23, 25) |
| after, on the 23 cases *not* used as few-shot | 23/23 = 100% | 22.25/23 = 97% (v1 on the same 23: 22/23 = 96%) |

**How to read this.** The headline moved from 88% to 100%, but the honest effect is smaller.
- The gain is concentrated on the two cases that were used as examples: E09 and E22 flip to agreement in 4/4 runs each.
- On the 23 held-out cases, agreement is 96% before vs 97% after, which is inside run-to-run noise.
- Haiku isn't deterministic. E07 and E21 change verdict between identical runs under both prompts.

The judge's PASS rate alone is 8/25 (32%) under v2, while the assertions pass 0/25. E02, E03, E09 and E23–E25 are judged "directly answers" but ship squashed code, v2-only symbols or repeated sentences. **A judge-only score would have told DevRel a third of these answers are fine.** The split is what catches the rest.

## 5. Prediction, written before the iteration, and where it was wrong

`prediction.txt` (file time 16:03:01 UTC, before the judge_v2 run at 16:03:28):
> adding E09 and E22 as few-shot examples will fix exactly those two and nothing else, so agreement goes from 22/25 (88%) to 24/25 (96%), E07 stays the only disagreement, and on the 23 cases not used as examples agreement stays at 22/23 (96%).

| Part of the prediction | Outcome | Right? |
|---|---|---|
| E09 and E22 get fixed | Fixed in the recorded run and in 3/3 reruns | ✅ right |
| 22/25 → 24/25 | 25/25 recorded; 24.25/25 mean | ❌ wrong on the recorded run, right on average |
| "E07 stays the only disagreement" | E07 agreed in the recorded v2 run, but it's a coin flip under **both** prompts (v1 PASS in 3/4 runs, v2 PASS in 1/4) | ❌ wrong. E07 was never a stable disagreement; the recorded v1 result was one draw. |
| "nothing else changes" | **E21 got worse.** It was agreed in 3/4 v1 runs but only 2/4 v2 runs. The E22 example ("refusing is right when the chunks don't list the changes") spills onto E21, where rank 3 does name one removed API. | ❌ wrong. The few-shot had a side effect the prediction didn't foresee. |
| held-out stays 22/23 | 23/23 recorded; 22.25/23 mean | roughly right on average |

What I learned: with one recorded run per prompt, I predicted a deterministic outcome from a stochastic judge. The next prediction should be stated as a mean over at least 3 runs.

## 6. Disagreements: who was right

| Case | Human | judge_v1 | Who was right |
|---|---|---|---|
| **E09**: "TooManyRequestsError how to get the retry delay" | PASS | FAIL (assumed v3 because no version *string* was present) | **Human.** The criterion says to use the version the question asks about, and naming the v2-only exception is asking about v2. The answer (read `Retry-After` from `exc.response`) is correct for v2. judge_v2 got this right in 4/4 runs. |
| **E22**: "what changed between v2 and v3" → "I don't know" | PASS | FAIL (treated "This page lists behavioral changes…" as if it listed them) | **Human.** The chunk shown is only a pointer to a list; the changes themselves weren't retrieved. Refusing matches the rule "I don't know is PASS only if the documentation shown really doesn't contain the answer". |
| **E07**: "client.request example" → v2 `client.request(url="/v2/invoices")` code | FAIL | PASS (2 of 4 v1 runs) | **The judge, and my label is the error.** By the same rule I applied on E09 (naming a v2-only symbol means asking about v2), the v2 code *is* the direct answer. I labelled E07 as if the developer were on v3. The label isn't changed after the fact, because that would move the ruler. The real defect is that **the criterion doesn't say how to treat a question naming a v2-only symbol**, so both labeller and judge flip on it. |

**Next iteration (not done this week):** make that version rule explicit in the criterion. For example: "a question naming a v2-only symbol without a version is a v3 developer hitting the removal; PASS only if the answer points to the v3 replacement". Then do a fresh blind relabel of all 25 under the new wording, and measure over at least 3 judge runs.

---

## Files

`eval_set.jsonl` · `openapi_v3.json` · `deprecations.json` · `judge_v0_pre_split.txt` · `judge_v1.txt` · `judge_v2.txt` · `judge_v1_to_v2.diff` · `labeling_sheet.md` · `labels_25.json` · `labels_lock.json` · `prediction.txt` · `judge_runs/judge_v1.json` · `judge_runs/judge_v2.json` · `judge_runs/stability_3x.json` · `eval_table_before_judge.txt` · `eval_output_v1.txt` · `eval_output_v2.txt` (full terminal output of the one command)
