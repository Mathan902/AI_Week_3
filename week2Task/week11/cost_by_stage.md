# Cost per query, by stage

Source: the trace's own spans (`week11_logq.py stages --trace tr-a3d4b7eb86a5`). The generation cost is `total_cost_usd` from the claude CLI for that call (claude-haiku-5-5, list price $0.10 / $0.50 per MTok in/out; cache reads are cheaper). Retrieval and tools run locally, so they have no API charge.

## The incident request (`tr-a3d4b7eb86a5`, release v1)

| Stage | Cost | Share | Latency | Tokens |
|---|---|---|---|---|
| retrieval (MiniLM embed + top-4 search, local) | $0.0000000 | 0% | 9.8 ms | 8 embedded |
| tools (`check_deprecation`, local; none fired for this question) | $0.0000000 | 0% | 0.0 ms | 0 |
| generation (one haiku call) | $0.0001143 | 100% | 3,426.9 ms (API 1,968 ms; the rest is CLI start-up) | 1,310 in / 202 out |
| **total** | **$0.0001143** | | **3,436.9 ms** | 1,512 |

At list price, 1,310 in + 202 out would be $0.000232. The logged $0.000114 is lower because most of the input was a prompt-cache read. So this request is cheaper than the traffic mean.

## All traffic (700 production traces, v1)

| Stage | Mean cost / query | Share | p50 latency | p99 latency |
|---|---|---|---|---|
| retrieval | $0 | 0% | 11.4 ms | 116.6 ms |
| tools | $0 | 0% | 0.0 ms | 0.1 ms |
| generation | $0.0002172 | 100% | 3,875 ms | 7,623 ms |
| **total** | **$0.0002172** | | 3,889 ms | 7,634 ms |

## Before vs after the fix (same 20 last-week production questions, real calls)

| Release | retrieval | tools | generation | total / query | generation tokens in / out |
|---|---|---|---|---|---|
| v1 | $0 (33 ms p50) | $0 (0.0 ms; 0.10 calls/query) | $0.000177 | **$0.000177** | 1,227 / 329 |
| v4 | $0 (22 ms p50, two searches: scoped + shadow) | $0 (0.1 ms; 1.45 calls/query) | $0.000399 | **$0.000399** | 1,720 / 247 |

**What moved the number:** the fix made every query 2.3× more expensive, and all of the increase is generation input. The lookups the tools stage now finds (deprecation entries, plus the OpenAPI `x-sdk-call` for replacements) are pasted into the prompt: +493 input tokens per query. The retrieval and tools stages got more work (a second search, 14× more tool calls) and still cost $0 and under 0.1 s. So any cost optimisation has to target generation input: cache the static prompt prefix, and only inject a lookup when it changes the answer. Stage latency doesn't matter for cost here: generation is >99% of the time too.
