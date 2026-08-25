# Week 3 Task Set E — Results

**Scope statement:** only `corpus/sdk_v2/` (4 pages) and `corpus/sdk_v3/` (6 new reference pages + the migration changelog that shipped with them) were indexed. The rest of the docs site (`documents/`) was **not** re-indexed.

Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, cosine), unchanged across both arms. Vector store: **ChromaDB** (persistent local directory `chroma_data/`, no server or API keys) with metadata filtering. Only one variable was changed between arms: the chunker.

---

## 1. The 8 questions and their known-correct locations

Written from the pages **before** any search was run (see `questions.py`, committed before `eval_output/`).

| # | Question | Gold page | Gold section | Depends on |
|---|---|---|---|---|
| 1 | Type and default of `retry_backoff_ms` on `Client.send()`? | `v3-client` | Client.send() | parameter-table row |
| 2 | Exception on HTTP 429 and the attribute carrying the wait time? | `v3-errors` | RateLimitError | table + prose |
| 3 | Maximum file size accepted by uploads in v3? | `v3-files` | Upload parameters | parameter-table row |
| 4 | How to verify a webhook signature? | `v3-webhooks` | Signature verification | code fence |
| 5 | Default `buffer_size_ms` for streaming? | `v3-streaming` | Client.stream() | parameter-table row |
| 6 | Requests per minute on the free tier? | `v3-ratelimits` | Limit tiers | parameter-table row |
| 7 | How to disable automatic retries at construction? | `v3-client` | Client constructor parameters | prose under table |
| 8 | Which environment variable holds the API token? | `v3-client` | Authentication | prose + code fence |

## 2. Hit-in-top-5 over the SAME 8 questions, both strategies

| Q | Naive (120w/25ovl) | Structured |
|---|---|---|
| 1 | YES (rank 2) | YES (**rank 1**) |
| 2 | YES (rank 3) | YES (**rank 1**) |
| 3 | YES (rank 1) | YES (rank 1) |
| 4 | YES (rank 1) | YES (rank 1) |
| 5 | YES (rank 1) | YES (rank 1) |
| 6 | YES (rank 1) | YES (rank 1) |
| 7 | YES (rank 4) | YES (rank 1) |
| 8 | YES (rank 5) | YES (**rank 1**) |
| **Total** | **8/8** | **8/8** |

Secondary metrics computed from the same runs:

| Metric | Naive | Structured |
|---|---|---|
| Gold chunk at rank 1 | 5/8 | 5/8 |
| MRR | 0.760 | 0.750 |
| Queries where top-1 is a **stale v2** page | **3/8** | **0/8** |
| Chunks containing an unclosed code fence | **1** | **0** |

The headline number did not move (8/8 vs 8/8) — but the per-question record shows *where* naive loses: on Q1, Q2 and Q7 its top-1 hit is the outdated **v2** page (e.g. Q1's #1 result is `v2-client::client-request` describing `retry_backoff_ms = 2000`, the value v3 removed). Structured never puts stale content first and never breaks a code fence; naive did both. Full search-only dump for every question under both strategies: `eval_output/search_dump.md`.

## 3. Metadata filter changing retrieval (scores pasted)

Query: **"What happens when the API returns HTTP 429?"**

Unfiltered — the stale v2 page wins:

```
1. [v2] v2-errors #toomanyrequestserror      dense=0.572 final=0.647
2. [v2] v2-errors #error-class-table         dense=0.523 final=0.598
3. [v3] v3-errors #ratelimiterror            dense=0.517 final=0.592
4. [v3] v3-errors #error-class-table         dense=0.499 final=0.574
5. [v2] v2-client #client-request            dense=0.499 final=0.537
```

With `filters={"sdk_version": "v3"}`:

```
1. [v3] v3-errors #ratelimiterror            dense=0.517 final=0.592
2. [v3] v3-errors #error-class-table         dense=0.499 final=0.574
3. [v3] v3-client #client-send               dense=0.451 final=0.489
4. [v3] v3-ratelimits #handling-http-429     dense=0.427 final=0.464
5. [v3] v3-client #client-send               dense=0.410 final=0.448
```

Top-1 moves from `v2-errors::toomanyrequestserror::2` (renamed exception, no retry-delay attribute) to `v3-errors::ratelimiterror::2`.

## 4. Cited answers (citations resolve to real chunk_ids)

Generation searched with `sdk_version=v3` pinned (these questions are about v3); each citation resolves via `page_id + anchor` to a stored Chroma record whose metadata and document contain the claim.

1. **Q1:** `| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay…` — `[chunk:v3-client::client-send::6-table]`, anchor `#client-send`, source `client.md`
2. **Q4:** `verify_signature(payload=raw_body, signature_header=request.headers["X-Acme-Signature"], secret=…)` — `[chunk:v3-webhooks::signature-verification::2-code]`, anchor `#signature-verification`
3. **Q6:** `The free tier allows 60 requests per minute with a burst allowance of 10 requests.` — `[chunk:v3-ratelimits::limit-tiers::2]`, anchor `#limit-tiers`

Verbatim transcripts are in `eval_output/search_dump.md`. The generation stage is **deterministic extractive by design**: it quotes the fact-bearing lines of the best-matching retrieved chunk and cites its `chunk_uid`, so every transcript is reproducible and every citation is verifiable by construction. Refusal is enforced by a two-stage gate (evidence score + lexical support), not by prompt suggestion — an LLM was deliberately not introduced, because the rubric's checkable property ("the cited chunk actually contains the claim") is guaranteed by quoting rather than paraphrasing.

## 5. Refusals (3/3 refused)

| Out-of-corpus question | Result |
|---|---|
| How do I rotate my account password with the SDK? | REFUSED |
| Does the SDK publish events to Kafka for stream processing? | REFUSED |
| How do I install the SDK with pip? | REFUSED |

All three returned exactly: `I don't know based on the provided documents.`

The refusal is **forced**, two-stage: (a) evidence gate — top-1 score < 0.40 refuses immediately; (b) lexical-support gate — if fewer than 60% of the question's salient terms appear in the top-3 chunks, refuse even when the score looks confident (this catches the Kafka case, which scored a seductive 0.589 against the streaming page). The prompt itself additionally forbids "best judgement" phrasing. Full transcripts pasted in `eval_output/search_dump.md`.

## 6. Topic clusters

KMeans over the stored chunk embeddings, with `k` chosen automatically by silhouette score (range 2–8). Each Chroma record's metadata gains `cluster_id` + `cluster_label`, so topic-restricted retrieval is a normal metadata filter (`cluster_id`), identical in mechanism to the `sdk_version` filter.

| Collection | k chosen | Silhouette | Example clusters (label → chunks) |
|---|---|---|---|
| `sdk_naive` | 8 | 0.199 | uploads-file-upload (3), toomanyrequestserror-exception-error (5), configured-method-verb (5) |
| `sdk_structured` | 8 | 0.124 | size-uploads-file (9), exception-after-raised (13), requests-iterator-free (7) |

Cluster code: `SdkVectorStore.create_clusters()` / `search_cluster()` in `vector_store.py`.

## 7. Which chunker ships, and why

**The structure-aware chunker ships.** On the primary metric it matched naive (8/8), so the decision rests on the failure modes the per-question record exposed: naive put a stale v2 page at rank 1 on 3 of 8 queries — including feeding our own generator `retry_backoff_ms = 2000` (a value v3 removed) with high confidence — while structured never did; naive also produced one chunk containing half a code fence, which would hand the model syntactically invalid context exactly where code examples matter most. Structured costs more chunks (62 vs 21) but chunk count is not a quality signal, and Q6 shows its payoff directly: the free-tier question scored 0.931 against an intact limit-tiers table versus naive's 0.704 against blended prose.

### Retrieval that embarrassed us (diagnosed)

During the first generation run, Q1's cited answer quoted **`retry_backoff_ms | int | 2000`** — the v2 table row, presented as the v3 answer, by a chunk-selection step that ranked purely on keyword coverage and score. Diagnosis: the generation stage inherited unfiltered retrieval, so version-conflicting near-duplicates competed and the stale one won on surface overlap. Fix: pin `sdk_version=v3` at the generation stage (questions name the target version), keep retrieval honest and unfiltered for measurement. This is the same bug class the metadata-filter demo quantifies — caught here at answer time, not just ranking time.
