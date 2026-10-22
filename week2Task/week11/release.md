# Release record: prompt v1 → v4 (deprecated code samples for v3 developers)

Each release is a prompt file plus the retrieval and tools settings shipped with it (`RELEASES` in `week11_app.py`). Every trace logs `prompt_version` and `prompt_sha`.

| Release | Prompt (sha) | Change | Suite (3 runs, of 28) |
|---|---|---|---|
| **v1** (live) | `answer_v1.txt` (`7da4c4e195c2`) | as shipped: unscoped top-4 over v2 + v3 pages, deprecation lookups on the question only | 20 · 20 · 19 |
| v2 | `answer_v2.txt` | **retrieval:** scope to the developer's SDK version (`retrieval_scope`: v3 unless the question says v2; no filter when it names both or asks to migrate), plus a "shadow" unscoped search whose archived v2 hits are never shown to the model but feed `check_deprecation`. **tools:** lookups over question + retrieved + shadow text. **prompt:** no deprecated or renamed name in target-version code | 25 · 27 · 27 (W11-02 judge FAIL 3/3: it named `list_after()` but showed no usage) |
| v3 | `answer_v3.txt` | **tools:** fetch the OpenAPI entry (`x-sdk-call`) for each `replacement_path` a lookup returns. **prompt:** base the code on it | 26 · 27 · 27 (E08 3/3: "not `upload_file`" counts as no migration note; W11-03 1/3: v2 answer dropped the "removed in v3" note) |
| **v4** (candidate) | `answer_v4.txt` | **prompt only:** say "removed in v3" / "renamed in v3"; for v2 developers give v2 code plus one sentence on what v3 removed | **28 · 28 · 27** |

The v2 per-case `.jsonl` files were overwritten by the v3 runs. Their pass counts above are from the terminal output. The v3 runs are kept in `week11/suite_runs/`.

**Cost of the fix:** $0.000177 → $0.000399 per query (generation input 1,227 → 1,720 tokens, from the injected lookups), measured on 20 production questions. See `cost_by_stage.md`.

## Canary and rollback

1. **Canary:** serve v4 to 10% of users (hash of `user_id`) for 48 h and compare against v1 on the same day. Promote only if (a) `output_index.flags` shows zero `deprecated_call_in_code` for v4 (v1 runs at 5.6%), (b) the 28-case suite stays ≥ 27/28, and (c) v4's "I don't know" rate and p99 latency are within +2 points / +20% of v1's.
2. **Rollback:** set `LIVE = "v1"` (one line; no data migration, because every trace carries `prompt_version`, so v4 traffic stays separable). Roll back if any v4 trace is flagged `deprecated_call_in_code`, the refusal rate rises > 2 points, or cost per query passes $0.0006 (1.5× the measured $0.0004).
