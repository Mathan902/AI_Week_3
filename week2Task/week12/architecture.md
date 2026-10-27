# Architecture: SDK Docs Answer Engine (one page)

```
 IDE plugin / CLI                       capstone.py ask "..." --sdk-version 2.4          (one entry point)
        │  question + installed SDK version
        ▼
 ┌─────────────────────────────── week12_engine.Engine  (the MCP HOST; all model calls happen here) ───────────────┐
 │                                                                                                                  │
 │  [s1 intake]  redact() secrets ──► resolve_version()  flag > "on 2.4" in text > v2-only symbol in pasted code     │
 │      $0, <1 ms        │                │                 > default 3.0 (and the answer says it assumed)          │
 │                       │                ▼                                                                         │
 │                       │        Resolved{major v2, minor 2.4, code_target v2, allowed [v2]}                       │
 │                       ▼                                                                                          │
 │  [agent.lap 1..8]  ◄══ LLM CALL (claude-haiku via `claude -p`) ══►   Week 7 plan → act → observe loop            │
 │   ≈ $0.0004-0.001 each,  │  {"tool": ..., "args": ...}                budgets: 8 laps, $0.06, 150 s              │
 │   ~100% of the money     ▼                                                                                       │
 │                   version PIN (r2): sdk_version not in allowed → rewritten to 2.4, logged as `enforced`          │
 │                          │  tools/call  + _meta {trace_id, parent_span}                                          │
 └──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┘
                            ▼  stdio JSON-RPC (MCP)                        ◄── also reachable by any MCP client:
 ┌──────────────── week12_server.py  "acme-docs"  (no model call) ────────┐    Inspector / Claude Code / other squad
 │  search_docs(query, sdk_version)   Chroma where={"sdk_version": v2}    │
 │      Week 3-4 structure-aware chunks, MiniLM embed (local, $0, ~50 ms) │
 │  check_deprecation(symbol, sdk_version)  changelog + changed_in 3.0    │
 │  symbol_exists(symbol, sdk_version)      symbol table built from docs  │
 │  get_openapi_spec(path)                  v3 OpenAPI                    │
 │  resource docs://version-support-matrix  (attached, not a tool turn)   │
 │  → server span under the SAME trace_id → logs/mcp_server-*.jsonl       │
 └────────────────────────────────────────────────────────────────────────┘
                            │ result (+ _trace echo, stripped before the model sees it)
                            ▼
 ┌─ back in the host ──────────────────────────────────────────────────────────────────────────────────────────────┐
 │  [code_check]  ast.parse + imports resolve + every client method / kwarg exists in SDK v2  ($0, ~1 ms)           │
 │        fail → ONE repair lap (another LLM call) with the violations → still fail → code withheld, said so        │
 │  [render]  answer · code · "Version notes (SDK 2.4)" from the changelog (deprecations surfaced unasked)          │
 │            · citations = only chunk ids a tool returned in THIS trace, each with its SDK version + page link     │
 │  log: redact_obj(trace) → logs/requests-YYYY-MM-DD.jsonl   (one trace id, every span: latency, tokens, $)       │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 Offline, same entry point:  capstone.py eval  → week12_eval.py: 33 cases → 12 assertions → trajectory (13 cases)
                                                → Week 6 judge_v2 (one LLM call per case) → agreement vs locked hand labels
```

## Where the model calls happen

| Place | Calls per question | What it costs |
|---|---|---|
| Agent lap (host) | 2-6, mean in `cost_and_10x.md` | all of the per-question cost |
| Repair lap (host, r2 only, only when the code check fails) | 0-1 | one more lap |
| Judge (eval only, never in production) | 1 per eval case | eval cost only |
| MCP server, retriever, symbol table, changelog, redaction, version resolution | **0** | $0, local CPU |

## Where the money goes

Every dollar is agent-lap input tokens. Each lap re-sends the system prompt (tool catalogue from `tools/list`, about
2,700 tokens) plus every earlier tool result, so a 4-lap question pays for that prompt 4 times. Retrieval, the MCP hop,
the code check and logging cost nothing per request. The levers are therefore: fewer laps (pre-fetch the obvious
`search_docs` call), a cached system-prompt prefix, and a smaller tool catalogue. Figures are in `cost_and_10x.md`.

## The three releases the numbers compare

| | r0 Tuesday wiring | r1 prompt fix | r2 shipped |
|---|---|---|---|
| MCP server | Week 9 `week9_docs_server.py` | Week 12 `week12_server.py` | Week 12 |
| Prompt | Week 9 "you answer with v3 code" | version-aware | version-aware |
| Caller's version reaches retrieval as | words appended to the question | words in the prompt | a metadata filter the host enforces |
| Code check vs caller's symbol table | none | none | yes, with 1 repair, else withheld |
| Version notes / deprecations | whatever the model writes | whatever the model writes | generated from the changelog |
| Citations | as written | as written | only ids a tool returned |
| Trace id across the MCP hop | lost (server has no span) | kept | kept |
