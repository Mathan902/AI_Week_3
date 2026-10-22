# Week 11 support drill: find the code sample that used a deprecated method

**Complaint (all we got):** "a dev said it gave a code sample using a method we deprecated, some time last week."
No trace id, no user, no SDK version.

| | Drill 1 | Drill 2 (bonus, after the fix to the logs) |
|---|---|---|
| **Time-to-find** | **00:37** (10:20:09 → 10:20:46 UTC, 2026-10-21) | **00:11** (10:41:47 → 10:41:58 UTC) |
| **Slice that found it** | time (last week) → **output content**: regex over the generated code → sdk_target v3 → context-id cross-check | time (last week) → **output index**: `--flag deprecated_call_in_code` |
| **Found** | `tr-a3d4b7eb86a5` (`timeout_s`) | `tr-c4c1d08790dc` (`Client.upload_file()`) |
| **Correct?** | yes, matches the sealed receipt | yes, matches the sealed receipt |
| **Planted by** | a squadmate (see "Who timed it") | a squadmate, a fresh one |

**Who timed it.** There's no human squadmate in this repo. Each plant was done by a separate subagent that played the squadmate. It chose the trace, edited the logs, and wrote a sealed receipt (`week11/drill/sealed/plantN_receipt.json`, plus a copy of the original day file). Its only reply to me was the complaint sentence above. I started the clock (`date -u +%s` → `week11/drill/.t1_start`) before my first query and stopped it after I had picked a trace. Only then did I open the receipt. The clock is wall time for an agent typing queries, so it's faster than a human would be. Also, the finder (me) built the logger and knew the deprecation list. **Before Monday, re-run both drills with a human squadmate planting and timing:** `____________` (name).

## Drill 1, step by step (`week11_logq.py`, logs only)

| # | Query | Rows left |
|---|---|---|
| 1 | `stats`: 700 traces, 2026-10-05..10-20, all prompt v1 | 700 |
| 2 | `find --since 2026-10-12 --until 2026-10-19` (time slice: "last week") | 294 |
| 3 | `find ... --code-re 'paginate_auto\|upload_file\|\.request\(\|timeout_s\|TooManyRequestsError\|/v2/'` (**output**, not input: the deprecated call is in the generated sample) | 19 |
| 4 | keep `sdk_target == v3` (a v2 developer *should* get v2 code) | 15 |
| 5 | per candidate: deprecated symbols in the code vs the retrieved context ids | one stands out |
| 6 | `find --q-re '^set timeout to 2 minutes$'` (same question across the logs) | 5 traces, 4 answered `timeout_ms` |

**Why `tr-a3d4b7eb86a5`.** Its top retrieved context is `v3-changelog::timeout-units-renamed::2`, which says "`timeout_s` is now `timeout_ms`". It also cites `v3-client::client-constructor-parameters::3-table`. Both are v3 pages that say the opposite of its code: `Client(timeout_s=120)`. The other four traces with the same question and the same top context all answered `timeout_ms`. So the code wasn't served by retrieval, and the context ids are what showed that in one hop.

Slices that did **not** help, because the complaint gives no handle for them: user (no user named), prompt version (all v1), input type (it's a plain `question`), and cost outlier (`$0.00011`, below the $0.00022 mean). A slice of mine that also failed: output chars per billed output token, meant to spot a hand-edited output. It's bimodal because of prompt caching, so it separates nothing.

## The missing field (it cost seconds here, and would cost minutes for a human)

I was under 5 minutes, but two things in step 3 and step 5 depended on me rather than on the logs:
1. **I had to know every deprecated symbol** to write the step-3 regex. The trace had the output text, but no *index* of the output. Searching the question would have found nothing: the incident question "set timeout to 2 minutes" contains no deprecated symbol.
2. **I had to hand-write a script** to put each candidate's code next to its retrieved context.

**The field that closed the gap: `output_index`** (trace schema 2). It's computed when the trace is written (`week11_logq.output_index`, called from `DocsAssistant.ask`) and backfilled for old traces by `week11_logq.py reindex`:
```json
"output_index": {"deprecated_in_code": ["Client.upload_file()"],
                 "served_from": {"Client.upload_file()": "retrieved_v2_page"},
                 "flags": ["deprecated_call_in_code"]}
```
`flags` also carries `code_contradicts_context` when the deprecated symbol is in no retrieved v2 chunk. That covers "the model wrote it from memory", or a trace altered after the fact, which is how drill 1's plant looked.

**Drill 2:** `reindex` → `find --flag deprecated_call_in_code --since 2026-10-12 --until 2026-10-19`. That's one query: 294 → 16 rows. The second plant edited a trace whose retrieved context *did* include the archived v2 uploads page, so `code_contradicts_context` (5 rows, all already seen in drill 1) did not catch it. The last hop was "which of the 16 is not in drill 1's triaged list": exactly one, `tr-c4c1d08790dc`. In production that triaged list is the incident ticket's trace list, so it's a fair hop. But without it, a human would read 16 rows, not 1.

## What the slice also showed: the bug is systemic

The planted answer was a hand edit. The real v1 app answered "set timeout to 2 minutes" correctly in 4/4 production traces, and in 0/3 RED runs did it emit `timeout_s`. But the same slice found that **38 of 675 real v3-target requests (5.6%) shipped a deprecated call in the generated code**, 14 of them last week. **29 of the 40 flagged traces** carry the deprecated symbol in a retrieved v2 chunk (`served_from: retrieved_v2_page`): retrieval served the archived v2 page and the model copied it. Example: `tr-bc9b9c00ce4a`, "how do I iterate every invoice" → `client.paginate_auto(url="/v2/invoices")`, with `retrieved_context_ids[0] = v2-pagination::paginate-auto::3-code`. That's why the eval file has three cases, not one (see below), and why the fix is at the retrieval layer, not just the prompt.

## Failure → test → fix

- **Eval cases:** `week11/eval_cases.jsonl`, loaded with the 25 Week-6 cases by `week11_suite.py`.
  - `W11-01` is the complaint's question; its code must not match `\btimeout_s\b`.
  - `W11-02` is the reproducible sibling from the same slice; its code must not match `paginate_auto` or `/v2/`, and it must mention `list_after`.
  - `W11-03` is the v2-legacy guard: a v2 developer must still get `paginate_auto` and not `list_after`. It's there so the fix can't quietly break v2 support.
  - New assertion `no_deprecated_call_in_code`. The Week-6 deprecation assertion passes any answer that says "removed" anywhere, even while the code block still calls the removed method.
- **RED, then GREEN, with pass counts:** see `week11/suite_red_r*.txt`, `week11/suite_green_r*.txt` and the per-case table in `week11/suite_summary.md`.

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| RED, release v1 (before the fix) | **20/28** | **20/28** | **19/28** |
| GREEN, release v4 (after) | **28/28** | **28/28** | **27/28** |

  - Every case passes at least as often after as before (no regressions), and 10 cases move from failing to passing.
  - The 27/28 is W11-03 with a judge FAIL whose own reason ends "the verdict should be PASS rather than FAIL", with all 9 assertions passing. It's counted as a fail anyway; the gate is the gate.
  - Each side ran 3 times because two v1 runs of the identical code differed by 4 cases (16/28 → 20/28).
  - `suite_red_initial.txt` (16/28) is the first RED run, before I marked W11-03 as v2-scoped. On that run the Week-6 `endpoints_in_spec` check only knows the v3 OpenAPI file, so any correct v2 sample failed it.
- **The fix and the version bumps:** see `week11/release.md`.
