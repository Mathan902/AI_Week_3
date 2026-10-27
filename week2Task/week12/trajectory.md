# Trajectory eval on the integrated agent (Week 8 method)

13 of the 33 eval cases carry **accepted paths, asserted as sets** (any order, any one alternative). A matcher checks
the tool, the `sdk_version` **the model chose** (before the host's pin, so the host can't launder a wrong choice),
and, for `search_docs`, that the results really contained the needed page. Scored from the same traces as the eval
run, with no extra model calls: `week12_eval.score_trajectory`, re-scored on load (`rescore_trajectory`).

Trajectory PASS (Week 8 strict) = an accepted path covered, no wrong tool, no host-pinned version, no tool error, no
repeated identical call, laps ≤ 2x optimal, and a final answer. Outcome PASS = all 12 assertions.

## Numbers

| Run | Tool-choice accuracy | Outcome | Trajectory (strict) | **Gap** (outcome - trajectory) | Evidence-only path | Laps taken / optimal |
|---|---|---|---|---|---|---|
| r0_a | 27/29 (93.1%) | 2/13 (15.4%) | 7/13 (53.8%) | **-38.5 pts** | 8/13 | 3.23 / 2.15 |
| r1_a | 55/55 (100%) | 9/13 (69.2%) | 5/13 (38.5%) | **+30.8 pts** | 11/13 | 5.08 / 2.15 |
| r2_a | 50/50 (100%) | 11/13 (84.6%) | 5/13 (38.5%) | **+46.2 pts** | 13/13 | 4.85 / 2.15 |
| **r2_b** | **55/55 (100%)** | **11/13 (84.6%)** | **6/13 (46.2%)** | **+38.5 pts** | 12/13 | 5.15 / 2.15 |

## What the gap says (the embarrassing part)

- **r0's gap is negative: right path, wrong answer.** In C11, C12, C15, C16 and C18 r0 retrieved the right evidence
  and still failed. The Week 9 prompt told it to write v3 code, so it searched the v2 page and then wrote v3 code
  anyway (C01: `search_docs(v2) → get_openapi_spec(/v3/invoices) → final` with `list_after`). The path was fine; the
  instruction was wrong.
- **r2's gap is positive: right answer, long path.** Every r2_b trajectory failure is "N laps vs 2 optimal". There
  is no wrong tool (100% tool choice), and evidence is missing only where the run hit the budget (12/13 paths covered; C16 ran out of laps). Right answer, wrong path:
  C03, C11, C15, C26, C27. Typical shape, C03: `search symbol check_ check_ symbol final`, 6 laps where
  `search → final` is enough. The extra laps are the prompt's own rules ("call check_deprecation on every v2 symbol",
  "symbol_exists if unsure") being followed too literally.
- **This is the same behaviour as the verification spiral (taxonomy mode 1).** When the extra checks fit inside the
  8-lap budget, the answer is right and the path is 2.5x too long (trajectory FAIL, outcome PASS). When they don't
  fit, the answer is "I don't know" (C16 in r2_b: 8 laps, budget exceeded). The trajectory gap is the early warning
  for the outcome failure.
- **Cost of the long path:** on these 13 cases r2_b takes 5.15 LLM calls per question against 2.15 optimal (5.58 over
  all 33 cases). At
  $0.00056 per lap, the extra laps are most of the bill (`cost_and_10x.md`).

## The case that shows it

`tr-008ab778c2af` (r2_b C23, "client.paginate_auto(...) is slow, how do I change the page size?"): lap 1
`symbol_exists(client.paginate_auto, 2.x)` already returns `params: [page_size, url]`. Lap 2 `search_docs` returns
the v2 pagination table with `page_size`. Laps 3-8 check `page_size` and `Client` in the changelog, `Client` in the
symbol table, then search for "how to construct Client" twice. Budget exceeded, "I don't know". Trajectory says
"evidence covered by lap 2", outcome says FAIL: the two evals disagree, and the trace explains why.
