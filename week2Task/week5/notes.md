# Week 5 Task Set E: Notes

The system under test is the pipeline shipped after Week 4: the **baseline** retriever (dense MiniLM plus lexical boost, `sdk_structured`, k=3; hybrid was rejected) feeding the deterministic extractive generator (`generate.py`, score gate 0.40, lexical-support gate 0.60). There is no LLM.

**Traffic source (honest note):** this repo has no production query log. `week5/traffic_questions.txt` holds 126 developer questions that I wrote in one pass *before any trace was generated or read*. They cover v2 and v3 users, migration, symptom-first phrasing, typos, code requests and out-of-corpus asks. The 12 golden-set (DX demo) questions are excluded. Each question was traced once → `week5/traces.jsonl` (126 traces, one JSON line each).

**Freeze proof:** the tracing code, the traffic pool, all 126 traces and the seeded sample were committed in `5f58d51f` *before* any trace was read. Between that commit and the prediction commit, the only files added are data and write-ups (`notes.md`, `taxonomy.md`, `prediction.md`, `replay_evidence.json`, `demo_*`). **No `.py` file changed.** Check with `git diff 5f58d51f --stat -- '*.py'`.

---

## 1. Replay evidence

**Seed 921** → `random.Random(921).sample(sorted(trace_ids), 1)` → **`tr-fccf2600b5`** ("how do I stream events"). Reproduce with `.venv/bin/python week5_run.py replay --seed 921`. Full record: `week5/replay_evidence.json`.

| | Output |
|---|---|
| **Original** (from `traces.jsonl`) | `with client.stream(url="/v3/events") as events: ```python with client.stream(url="/v3/events") as events:     for event in events:         print(event.type, event.data) ``` [chunk:v3-streaming::client-stream::4-code]` |
| **Replayed, generation from the trace alone** (hits rebuilt from stored chunk text + scores, gates from stored params and `common_terms`) | identical, byte for byte |
| **Replayed, full pipeline** (retrieval re-run from stored query + collection + top_k + filters) | identical, byte for byte |

The retrieved chunk IDs and the dense and final scores match to 6 decimals:
`streaming-responses::0` 0.582412/0.612412, `client-stream::4-code` 0.529183/0.589183 and `client-stream::1` 0.479847/0.509847.

The versions are the same in the trace and now: generator `83e35f5a3ae0`, retriever `7a5ba5a1aba5`, corpus `abdce489cb24`, embedder `all-MiniLM-L6-v2@1110a243`.

**Fields that were missing, so I added them.** Before this week, the only per-request record was `week4_output/*.json`, which stored the question, the top-3 chunk IDs and the answer. It had **no retrieval scores, no gate params (threshold, support floor, top_k, filters, lexical boost), no `common_terms` set, no model name or revision, no generator or corpus version, and no chunk text**. From those records you cannot tell *why* a refusal happened. `tracing.py` now logs all of them, plus latency and a session tag. "Prompt version" becomes `generator_version` (a hash of `generate.py`), because no prompt template exists.

**What I still cannot reconstruct:**

1. I can't prove the embedder weights. I record the HF cache ref for the revision, not a hash of the loaded weight files.
2. Chroma's HNSW index is approximate and rebuilt on every start. Full-pipeline replay only matches because the index is rebuilt from the same corpus version, while generation-only replay does not depend on it.
3. Latency isn't reproducible.
4. The `session` tag is synthetic, so there is no real user context to replay.

---

## 2. Seeded random sample

`random.Random(20260921).sample(sorted(trace_ids), 20)` over the 126 trace IDs. The seed is today's date. Reproduce with `week5_run.py sample --seed 20260921`. The reading view with all retrieved text is in `week5/sample.md`.

```
tr-e144a5320d tr-3e5524039d tr-0a8782a5ac tr-3002ea968a tr-16cdcfb0f1
tr-d437a02c10 tr-0c614eb7d9 tr-b533926bc3 tr-2c606428b8 tr-59ebac9e56
tr-4fc05e9928 tr-b67ebb71de tr-4e8ace72b2 tr-4da0dedb22 tr-4fc7b3e2f0
tr-eb85fc3c25 tr-4a0095b313 tr-b292e79be2 tr-16c2469574 tr-66dbda2dd0
```

---

## 3. Open coding: 20 sentences, verbatim, written before any grouping

| # | trace_id | Question | What I saw |
|---|---|---|---|
| 01 | `tr-e144a5320d` | what was the old default backoff | It correctly answered "2000 ms in v2" from the changelog, but the second sentence is printed twice in a row. |
| 02 | `tr-3e5524039d` | how do I send json in the body of a request | The answer only says `Client.send()` "performs a single HTTP request and returns a Response". It never mentions `body=`, even though the v3 example with `body={"amount": 4200}` was retrieved at rank 3. |
| 03 | `tr-0a8782a5ac` | what is retry_backoff_ms | The answer only says the per-request parameter overrides the constructor value. It never says it is the base delay for exponential backoff or gives a default, and the v3 constructor table was not in the top 3 (the v2 table with 2000 was at rank 3). |
| 04 | `tr-3002ea968a` | how long can I resume an upload for | It answered "within 24 hours by passing the returned `upload_id`" from the v3 files page, which is correct and complete. |
| 05 | `tr-16cdcfb0f1` | paginate_auto example | All 3 chunks were v2. The answer describes `paginate_auto()` as walking every page, with no code and no mention that it was removed in v3, although the chunk at rank 2 says exactly that. |
| 06 | `tr-d437a02c10` | how do I test webhooks locally | It said "I don't know". None of the retrieved chunks mentions local testing, so the refusal matches what the docs contain. |
| 07 | `tr-0c614eb7d9` | create invoice example | It said "I don't know", but rank 3 held a v3 `client.send(url="/v3/invoices", method="POST", body=...)` example. Ranks 1 and 2 were v2 code. |
| 08 | `tr-b533926bc3` | webhook retry schedule | All three retrieved chunks are about HTTP 429 rate-limit retries, none from the webhooks Retries section, and it said "I don't know". |
| 09 | `tr-2c606428b8` | list_after usage | It quoted the changelog line that `list_after()` replaces `paginate_auto()`, with that clause printed twice. It gave no call signature or example, and none exists in the retrieved text. |
| 10 | `tr-59ebac9e56` | what is part_size_mb | It quoted the sentence that multipart activates above `part_size_mb` but never said what it is or that the default is 5. The table row "Size of each multipart chunk … 5" was at rank 2. |
| 11 | `tr-4fc05e9928` | what attribute tells me how long to wait after rate limit | It correctly named `retry_after_seconds` on `RateLimitError`, but the second sentence is printed twice. |
| 12 | `tr-b67ebb71de` | how do I override backoff for a single request | It answered correctly from the v3 page (the per-request `retry_backoff_ms` overrides the constructor), even though the v2 table was ranked 1. |
| 13 | `tr-4e8ace72b2` | NotFoundError retryable? | The answer talks about retries applying "to retryable errors listed in the table above" and repeats that clause, but never says NotFoundError is **not** retryable, although both error tables at ranks 1 and 2 say "no". |
| 14 | `tr-4da0dedb22` | what changed between v2 and v3 | It said "I don't know". Rank 1 was only the changelog's one-line intro, and none of the three change sections (retry defaults, timeout rename, removed APIs) was in the top 3. |
| 15 | `tr-4fc7b3e2f0` | what happens if the stream disconnects | It said "I don't know" even though the rank-1 chunk says the SDK reconnects automatically with backoff and replays missed events. I don't know why this one refused. |
| 16 | `tr-eb85fc3c25` | AuthenticationError when creating client | The answer is right (a missing token raises it; set `ACME_API_TOKEN`) but it is cited to the v2 page, not the identical v3 one, and repeats its first sentence. |
| 17 | `tr-4a0095b313` | v2 upload limit vs v3 | It said "I don't know" while ranks 1 and 2 contain both numbers (v3 25 MB, v2 10 MB). I don't know why this one refused. |
| 18 | `tr-b292e79be2` | how to verify webhook payload | The output is the Python code sample squashed onto one line (backticks and all), followed by a second copy of the import line, so it can't be pasted and run. |
| 19 | `tr-16c2469574` | what scheme does verify_signature expect | The output is `from acme.webhooks import verify_signature verify_signature(`, a call cut off mid-argument. It never says "v3", which was in the table at rank 3. |
| 20 | `tr-66dbda2dd0` | list of removed apis in v3 | It said "I don't know". The changelog "Removed APIs" chunk wasn't in the top 3: rank 1 was the changelog intro, and ranks 2 and 3 were v2 pagination text. |

Clean passes: 04, 06, 12. Correct content with only a repeated sentence: 01, 11 (and 16).

---

## 4. Taxonomy

→ `week5/taxonomy.md` (one screen).

## 5. Dated prediction

→ `week5/prediction.md`, committed on **2026-09-21** in commit **`fbaefa6a`**, before any fix.

---

## 6. Why a public benchmark would not have surfaced the top-3 modes

A public benchmark like MMLU or HumanEval scores a model on public questions with public reference answers, and the generator here isn't even an LLM, so no leaderboard number describes this system at all. My top-3 modes (a code sample flattened onto one line or cut off mid-call, a removed v2 API presented as current, and an answer that quotes the sentence next to the fact instead of the fact) come from *this* app's extraction step, *this* corpus's mix of v2 and v3 pages and *this* retriever's chunk choice, and none of those exist in any benchmark's inputs. The only way these showed up was reading our own traces against our own docs.

---

## 7. Bonus: 10 traces from the curated demo set

These are the 10 golden-set questions the team shows at the DX review. The draw was `random.Random(20260921).sample(sorted(golden ids), 10)` = Q04, Q01, Q12, Q02, Q11, Q07, Q06, Q09, Q10, Q05. They were traced through the same pipeline into `week5/demo_traces.jsonl` (reading view: `week5/demo_sample.md`).

| # | trace_id | Question | What I saw |
|---|---|---|---|
| D1 | `tr-eb756d46af` | uploads keep failing with PayloadTooLargeError, what's the size limit? | It said "I don't know" while the rank-1 v3 table row says `max_file_size_mb` 25. |
| D2 | `tr-d898260ff2` | what is the default for retry_backoff_ms | It quoted the per-request override sentence and never gave a value, while the changelog with "500 ms in v3" was at rank 3. |
| D3 | `tr-f4296b1de7` | how many times does a failed webhook delivery get retried? | It said "I don't know" while the rank-1 chunk says "up to five times over six hours". |
| D4 | `tr-b52c17cd99` | how do I authenticate the client? | It said "I don't know" while ranks 1 and 2 both say to set `ACME_API_TOKEN`. |
| D5 | `tr-48b7c63837` | timeout_s stopped working after the upgrade, what's the new option? | It said "I don't know" while the rank-1 changelog chunk says `timeout_s` is now `timeout_ms`. |
| D6 | `tr-2e7bca4968` | paginate_auto is gone after upgrading, what do I use now? | It said "I don't know" while ranks 1 and 3 both say to use `list_after()`. |
| D7 | `tr-28b455d072` | got a 429 back, how long should I wait before retrying? | It answered correctly (`retry_after_seconds` from `Retry-After`) but printed the second sentence twice. |
| D8 | `tr-f019715dc3` | can I share one client across threads? | It answered correctly (thread-safe, share one instance) but printed the second sentence twice. |
| D9 | `tr-6a26231079` | how do I resume an upload that got interrupted? | It answered correctly and completely (24 hours, `upload_id`). |
| D10 | `tr-a495636510` | what does X-RateLimit-Remaining mean? | It listed the three rate-limit headers "describing your current budget" but didn't say what Remaining counts on its own. The docs don't say either. |

**Top-ranked mode (code sample flattened or cut off): random sample 2/20 = 10%, demo set 0/10 = 0%.**
For comparison, "says I don't know while a top-3 chunk holds the answer" is 3/20 = 15% random vs **5/10 = 50%** demo. "Presents a removed v2 API as current" is 1/20 = 5% random vs 0/10 demo.

**What the team has been telling itself.** The demo set is 12 hand-picked questions built around exact symbols and refusals, and Week 4's whole effort (the hybrid retriever, the gate analysis) was tuned against it. So the team has been telling itself the assistant's problem is *refusing too much*, and that the rest works. On the demo set that looks true: half of it is wrongful refusals, and not one demo question produces a code sample, so the only mode that ships broken code into a user's repo is invisible at every DX review. On random traffic, wrongful refusal is 15%, not 50%. The larger share is answers that quote the sentence next to the fact (25%), and one in ten answers pastes mangled code. The DX lead's "sometimes gives outdated code" is real, but in the random sample it is 1 trace in 20. It is worth fixing, but it isn't the biggest problem, and the demo set couldn't show it either way.
