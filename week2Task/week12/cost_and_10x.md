# Cost per question, and what breaks first in-IDE

**Cost per question: $0.0031 mean (p50 $0.0028, max $0.0061), 100% of it LLM laps. p50 23.8 s, p95 38.6 s.**
**What breaks first when all 9,000 integrators get it in their IDE: the model's input-tokens-per-minute limit, at
121% of the limit (2.41M of 2.0M ITPM) in the peak minute on day one.** Each question re-sends a ~3.8k-token prompt
5.6 times (21,445 input tokens). Next to break: the $500/month spend cap on working day 6 (cost is 3.7x the cap), and
on a single host 9.6 GB of `claude` processes. At today's traffic (and at 10x today) nothing breaks except latency,
which is already too slow for an IDE.

## Cost per question, by stage (r2_b, n=33, real calls)

| Stage | Per question | Share of $ | Latency | Notes |
|---|---|---|---|---|
| intake (redact + resolve version) | $0 | 0% | <1 ms | local |
| agent laps (LLM, claude-haiku via `claude -p`) | **$0.00314** (5.58 laps x $0.00056) | **100%** | 4.2 s p50 / 6.9 s p95 per lap; 99.6% of wall time | 21,445 in + 2,475 out tokens per question |
| MCP hop (tools/call, client side) | $0 | 0% | 4.6 ms p50 / 62 ms p95 per call, 4.7 calls/question | stdio JSON-RPC |
| MCP server: `search_docs` (MiniLM + Chroma, version filter) | $0 | 0% | 44 ms p50 | local CPU |
| MCP server: `check_deprecation`, `symbol_exists`, `get_openapi_spec` | $0 | 0% | 0.1 ms | dict lookups |
| code check (parse + symbol table) | $0 | 0% | 0.2 ms | the free deterministic assertion |
| repair lap (only if the code check fails) | 0 laps fired in r2_a + r2_b | 0% | - | |
| render + log (redact on write) | $0 | 0% | <1 ms | |
| **total** | **$0.00314** mean, $0.00281 p50, $0.00614 max | | **23.8 s p50, 38.6 s p95** | |

Passing answers average $0.0028; the spiral answers ("I don't know" after 8 laps) average $0.0049. The most
expensive questions are the ones that fail. The `cost_usd` values are the claude CLI's `total_cost_usd` per call,
which already includes the prompt-cache discount.

For comparison: r0 (Tuesday wiring) cost $0.00188 at 3.7 laps. The fix made each question 1.7x more expensive
(+1.9 laps of checking), the same pattern Week 11 found (correctness fixes are paid for in input tokens).

**Re-indexing for v3.1:** embedding all 62 chunks takes 0.08 s, and a full server start (model load + chunk + embed +
index) takes 7.7 s, all local, $0. The symbol table is rebuilt from the docs at import. The cost of a docs change is
**which tests go red**: `DocsDrift.test_symbol_table_matches_snapshot` fails the moment v3.1's pages add or remove a
method or parameter, and `DocsDrift.test_every_changelog_entry_is_guarded_by_an_eval_case` fails until each new
deprecation has an eval case that must surface it. Both are in `capstone.py test`, at no model cost.

## Load: today, 10x today, and in-IDE

Rate limits are as recorded in `week11/tenx.md` (Haiku, Start tier: 1,000 RPM, 2,000,000 ITPM, 400,000 OTPM, $500 a
month). Re-check against the account's real tier before quoting them. Today's traffic is Week 11's measured
production: 44.2 questions/day, busiest minute 2.

| Scenario | Peak q/min | LLM RPM | **Input TPM** | Output TPM | Questions in flight -> `claude` RSS | $/month vs $500 cap |
|---|---|---|---|---|---|---|
| Today (Week 11) | 2 | 11 (1%) | 42,890 (2%) | 4,950 (1%) | 0.8 -> 0.2 GB | $4 (1%) |
| **10x today** | 20 | 112 (11%) | 428,900 (21%) | 49,500 (12%) | 7.9 -> 1.7 GB | $42 (8%) |
| **In-IDE, 9,000 integrators** | 112.5 | 627 (63%) | **2,412,562 (121%)** | 278,438 (70%) | 44.6 -> 9.6 GB | **$1,867 (373%)**, cap hit on working day 5.9 |

In-IDE assumptions, stated because they drive every cell: 3 questions per integrator per working day (27,000/day),
22 working days/month, peak minute = 2x the average minute of an 8-hour day. The ITPM wall is at 93 q/min peak, i.e.
2.5 questions per integrator per day, or 47x today's busiest minute. Input TPM is the worst case, with every token
counted. Cache reads don't count toward ITPM, and the CLI does not report the cached share per lap.

**Ordering: input TPM breaks first (121%), then the spend cap (day 6), then output TPM (70%, breaks at 162 q/min),
then RPM (63%, breaks at 179 q/min).** Latency doesn't "break" with load until in-flight work queues, but at p95
38.6 s it is already past any reasonable IDE budget at 1x.

## What to do next, ranked and costed

| # | Change | What it buys (estimate, to be measured by re-running `capstone.py eval`) | Cost |
|---|---|---|---|
| 1 | **Fix the verification spiral**: the host caps `symbol_exists` + `check_deprecation` at 3 calls per question, and on lap 7 sends "final answer now". The code check backstops any invented name. | Removes the 4/33 "I don't know" (mode 1) and the 8-lap tail. Laps 5.6 -> ~4 cuts input TPM ~28%, which alone does not clear 121% | ~2 h + one eval run (~$0.10) |
| 2 | **Host pre-fetch**: run the version-pinned `search_docs` before lap 1 and put the results in the first prompt | One lap fewer per question (~18% of tokens), and the pin is applied before the model chooses anything | ~1 h + $0.10 |
| 3 | **Anthropic SDK in-process, with prompt caching on the system prefix**, instead of a `claude -p` subprocess per lap | Removes ~1.5 s start-up and 215 MB per lap. If the ~2.7k-token prefix is cached each lap, uncached input falls to ~6.4k per question, ITPM at in-IDE peak drops to ~36%, and output TPM (70%) becomes the first wall | ~1 day; same per-token price |
| 4 | **Answer cache** keyed by (normalised question, SDK minor version, docs-index hash), invalidated by re-index | IDE questions repeat. Every hit costs $0 and ~0 s | ~1 day |
| 5 | Rate-limit tier increase + a monthly budget above $1,900 | Moves the walls; doesn't change $/question | admin |
| 6 | Bring in the SO answers + samples repo and measure keep vs drop hit-rate | Answers the hostile question this repo can't | needs the data |
