# Week 4 Task Set E: Results

**Label the failures, then buy back hit-rate@3 with exactly one change**

This builds on the Week 3 SDK-docs app. Both runs used the same setup:

| Held constant across both runs | Value |
|---|---|
| Corpus | `corpus/sdk_v2` + `corpus/sdk_v3`, structured chunker, 62 chunks |
| Embeddings / store | `all-MiniLM-L6-v2`, Chroma collection `sdk_structured` (rebuilt identically each run) |
| Generator | `generate.answer()`: deterministic extractive answer with a score gate (0.40) and a lexical-support gate (0.60) |
| Questions | `golden_set.jsonl` (the same 12 questions) |
| k | 3 |
| **Changed (the one variable)** | **retriever: `baseline` → `hybrid` (BM25 + RRF, k=60)** |

Reproduce with `python week4_eval.py --retriever baseline` and then `python week4_eval.py --retriever hybrid`. The full inspection views, which show the question, the top-3 chunks with scores and fusion ranks, the answer and the label side by side, are in `week4_output/inspection_baseline.md` and `week4_output/inspection_hybrid.md`. The raw per-question records are in `week4_output/*.json`.

---

## 1. Golden set: 12 questions, each with one known-correct chunk_id

The questions are written the way developers ask them: lowercase, starting from the symptom, and naming the symbol they're stuck on. They were written from the chunk list **before any search was run**. **Source note:** this repo has no support-ticket or search log, so the questions are modeled on typical developer phrasing and aren't copied from a log.

**8 of the 12** contain an exact token that dense retrieval handles poorly (4 are required).

| # | Question | Known-correct `chunk_id` | Exact token |
|---|---|---|---|
| Q01 | what is the default for retry_backoff_ms | `v3-client::client-constructor-parameters::3-table` | `retry_backoff_ms` (symbol) |
| Q02 | how do I authenticate the client? | `v3-client::authentication::1` | — |
| Q03 | what's the default heartbeat_interval_ms when streaming? | `v3-streaming::client-stream::2-table` | `heartbeat_interval_ms` (symbol) |
| Q04 | uploads keep failing with PayloadTooLargeError, what's the size limit? | `v3-files::upload-parameters::1-table` | `PayloadTooLargeError` (error class) |
| Q05 | what does X-RateLimit-Remaining mean? | `v3-ratelimits::headers::3` | `X-RateLimit-Remaining` (header) |
| Q06 | got a 429 back, how long should I wait before retrying? | `v3-errors::ratelimiterror::2` | `429` (error code) |
| Q07 | paginate_auto is gone after upgrading, what do I use now? | `v3-changelog::removed-apis::3` | `paginate_auto` (symbol) |
| Q08 | default tolerance_seconds for webhook signature checks? | `v3-webhooks::verification-parameters::3-table` | `tolerance_seconds` (symbol) |
| Q09 | can I share one client across threads? | `v3-client::thread-safety::9` | — |
| Q10 | how do I resume an upload that got interrupted? | `v3-files::resumable-uploads::4` | — |
| Q11 | timeout_s stopped working after the upgrade, what's the new option? | `v3-changelog::timeout-units-renamed::2` | `timeout_s` (symbol) |
| Q12 | how many times does a failed webhook delivery get retried? | `v3-webhooks::retries::5` | — |

**Scoring rule:** a question counts as a hit@3 only if **the one tagged `chunk_id`** is in the top 3. The file also lists `also_correct` chunks, meaning other chunks that state the same fact, and a lenient hit-rate is reported next to the strict one for transparency. The strict number is the scored metric, because the task defines the target as *the* chunk_id you know is correct. The lenient rule hides exactly the failure from the brief: for Q01, a changelog sentence counts as a lenient hit while the actual v3 parameter table is missing from the top 3.

---

## 2. Baseline: recorded before any change

**Baseline hit-rate@3 = 11/12 = 0.917** (lenient 12/12, MRR@3 0.722). **p50 retrieval latency = 4.55 ms.**

These numbers were saved to `week4_output/baseline.json` before `hybrid.py` existed. The baseline was re-run afterwards with the final harness, and all 12 per-question records came out identical.

---

## 3. Failure labels from the baseline inspection view

The labels mean:

- **R:** the known-correct chunk is not in the top 3.
- **G:** the correct chunk is in the top 3, but the answer doesn't contain the fact.
- **NIC:** no chunk in the indexed corpus holds the answer.

Each piece of evidence below is read directly off `inspection_baseline.md`.

| Q | Label | One line of evidence |
|---|---|---|
| Q01 | **R** | Gold v3 constructor table sits at dense rank **7**. All 3 of the top-3 contain `retry_backoff_ms`: `client-send::7` (prose), **`v2-client::client-request::5-table` (v2, default 2000)** and the changelog. |
| Q02 | **G** | Gold `authentication::1` is at rank 2 and contains `ACME_API_TOKEN`, but the answer was a refusal: the lexical-support gate scored 0.50, below 0.60 ("authenticate" ≠ "authentication"). |
| Q04 | **G** | Gold upload table is at **rank 1** and contains `25`, but the answer was a refusal: support 0.33 < 0.60. |
| Q07 | **G** | Gold `removed-apis::3` is at rank 3 and contains `list_after` (the v2 chunk at rank 1 says it too), but the answer was a refusal: support 0.57 < 0.60. |
| Q11 | **G** | Gold `timeout-units-renamed::2` is at **rank 1** and contains `timeout_ms`, but the answer was a refusal: support 0.43 < 0.60. |
| Q12 | **G** | Gold `webhooks::retries::5` is at **rank 1** and contains "five times", but the answer was a refusal: support 0.43 < 0.60. |

### Tally

| Label | Count | Questions |
|---|---|---|
| PASS (retrieved and answered) | 6 | Q03, Q05, Q06, Q08, Q09, Q10 |
| **R** (retrieval fetched bad context) | **1** | Q01 |
| **G** (good context, bad answer) | **5** | Q02, Q04, Q07, Q11, Q12 |
| Not-In-Corpus | 0 | — |

**What this says about swapping the embedding model:** 5 of the 6 failures are G. The right chunk was already in the top 3, usually at rank 1, and the generator's lexical-support gate refused anyway. No embedding model can fix a refusal that happens after correct retrieval. The single R failure isn't an embedding-quality problem either: dense retrieval already found three chunks that contain the exact symbol, and it just ranked the wrong ones first.

---

## 4. The one change and why it was chosen

**Change: BM25 keyword retrieval fused with the existing dense ranking by Reciprocal Rank Fusion (k=60), with both candidate lists 25 deep** (`hybrid.py`).

The baseline tally has one retrieval failure, Q01, and it is exactly the brief's `retry_backoff_ms` exact-symbol question. The top 3 were semantically close retry text (per-request override prose, the v2 request table, the changelog), and the v3 constructor parameter table sat at rank 7. BM25 exists for exact-token matches, so it was the retrieval change aimed at that failure. The 5 G failures can't be reached by any retrieval change and were deliberately not treated as justification.

RRF fuses **ranks**, never raw scores, because BM25 sums and cosine similarities aren't on the same scale. The dense arm is the unchanged baseline ranking. It was checked that the dense top 3 at depth 25 matches the depth-3 top 3 on all 12 questions, so the candidate depth isn't a hidden second variable. Returned hits keep their baseline scores, so the generator's gates see the same score scale, and only the order changes.

In hindsight, the inspection evidence already argued against this choice: **3/3 of Q01's top chunks already contained `retry_backoff_ms`**. The failure wasn't a missing keyword. It was ranking precision among four chunks that all contain the symbol, including a v2 table. BM25 matches the same token in all four and can't separate them. See section 6.

---

## 5. Before → after on the same 12 questions

| Metric | Baseline | Hybrid (BM25 + RRF) | Δ |
|---|---|---|---|
| **hit-rate@3 (strict)** | **11/12 = 0.917** | **10/12 = 0.833** | **−1 question** |
| hit-rate@3 (lenient) | 12/12 | 11/12 | −1 |
| MRR@3 | 0.722 | 0.694 | −0.028 |
| **p50 retrieval latency / query** | **4.55 ms** | **6.39 ms** | **+1.84 ms (+40%)** |
| p95 retrieval latency / query | 5.41 ms | 7.99 ms | +2.58 ms |
| p50 end-to-end (retrieve + answer) | 4.56 ms | 6.40 ms | +1.84 ms |
| Tally PASS / R / G / NIC | 6 / 1 / 5 / 0 | 5 / 2 / 5 / 0 | — |
| One-off BM25 index build | — | 4.8 ms | — |

**How latency was measured:** each run did one warm-up pass, then 12 questions × 7 repeats = 84 samples per run. Retrieval was timed with `perf_counter` in one process on local CPU (macOS). A second baseline run gave p50 = 4.91 ms, so run-to-run noise is about ±0.4 ms. The +1.84 ms cost is well above that. BM25 is pure Python over 62 chunks, and its cost grows linearly with corpus size.

### Per-question record

| Q | Gold rank before → after | Label before → after | Verdict |
|---|---|---|---|
| Q01 | miss → miss | R → R | **still broken; untouched** (identical top 3: BM25 ranked the same 3 chunks #1–#3, gold was BM25 #5) |
| Q02 | 2 → **miss** | G → **R** | **regressed**: `v2-client::client::0` (dense #4, BM25 #2) and `v3-client::client::0` pushed gold out; BM25 matched "client", but not "authenticate" to "authentication" (no stemming) |
| Q03 | 1 → 1 | PASS → PASS | unchanged |
| Q04 | 1 → 1 | G → G | unchanged (retrieval was never the problem) |
| Q05 | 1 → 1 | PASS → **G** | **answer regressed**: `v3-errors::error-class-table` (dense #12, BM25 #6, on the stopword "does") entered rank 2, and the generator quoted it |
| Q06 | 3 → 2 | PASS → PASS | rank improved; the answer was already correct |
| Q07 | 3 → 3 | G → G | unchanged |
| Q08 | 2 → 2 | PASS → PASS | unchanged |
| Q09 | 1 → 1 | PASS → PASS | unchanged |
| Q10 | 1 → 1 | PASS → PASS | unchanged |
| Q11 | 1 → 1 | G → G | unchanged |
| Q12 | 1 → 1 | G → G | unchanged |

**Fixed / unfixed / broken:** 0 fixed, 9 unchanged, 1 retrieval regression (Q02), 1 answer regression (Q05), 1 rank-only improvement (Q06).

---

## 6. Which original R failures the change fixed

The baseline had one R failure.

- **Fixed: none.**
- **Untouched: Q01.** The hybrid top 3 is byte-for-byte the baseline top 3. BM25 ranked the same three `retry_backoff_ms` chunks first and put the v3 constructor table at BM25 rank 5. The symbol appears in the gold table, the v3 send table, the v2 request table, the changelog and the override prose, so an exact-token signal has nothing to separate them with. The missing signal is "this is the v3 table row whose Default column answers *default*". That needs either a model that reads the query and chunk together (a cross-encoder rerank over the top 25; gold is at rank 7, so it's inside that window) or a version-aware filter or boost.
- **Newly created: Q02 (R).** This was caused by RRF's structure: a chunk ranked moderately on *both* lists (dense #4 + BM25 #2) outscores a chunk ranked high on only one. BM25 without stemming or stopwords gives a noisy second list on short natural-language questions.
- **None of the 5 G failures could move**, as expected, and none did (Q04, Q07, Q11, Q12 kept identical labels, and Q02 turned into an R).

---

## 7. Shipping decision

**Don't ship BM25 + RRF.** Hit-rate@3 went **0.917 → 0.833** (−1 of 12), p50 latency went **4.55 → 6.39 ms (+40%)**, and it fixed **0 of 1** R failures while adding an R failure and an answer regression. A change that costs latency and loses a question has no case, even on a small set where one question is 8 points.

**The embedding-model swap was declined too.** 5 of 6 failures are G, and the only R failure already had the exact symbol in all of its top 3. A new embedding model can't fix either.

**What the numbers point to next**, one change per run as before:

1. **Generator, not retriever.** The lexical-support gate refuses 5/12 questions whose gold chunk is at rank 1–3. Lowering or reworking that gate (for example, stemming "authenticate" → "authentication" and not counting symptom words like "gone", "upgrading" or "keep failing" as required terms) is worth up to +5 correct answers, with no retrieval latency cost.
2. **For Q01:** try a cross-encoder rerank over the dense top 25 as a *separate* single-change run against this same baseline, with its latency measured, or prefer `sdk_version=v3` when two chunks carry the same symbol.

Bonus (MMR): not attempted. This change isn't shipping, and MMR over the fused list would stack a second variable on top of a rejected one.

---

## 8. Code diff

`week4_change.diff` contains the full change against the pre-change baseline snapshot:

- `hybrid.py` (new): `bm25_tokens`, `BM25Index`, `rrf_fuse` (k=60) and `HybridRetriever`. This is the one retrieval change.
- `week4_eval.py`: registers `"hybrid"` next to `"baseline"`, and the inspection view gets a `fusion` column (dense rank, BM25 rank, RRF score). The inspection change is display only.
- `tests/test_hybrid.py` (new): symbol tokenization, BM25 exact-symbol ranking, and RRF rank arithmetic.

Files that were **not** changed between the two runs: `vector_store.py`, `chunking.py`, `generate.py`, `golden_set.jsonl` and the corpus.
