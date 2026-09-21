# Prediction: written and committed 2026-09-21, before any fix

**Mode attacked:** taxonomy rank 1, "Code sample comes back squashed onto one line or cut off mid-call". It is 2/20 (10%) in the seed-20260921 sample.

**The one change:** in `generate._extractive_cited`, when the chunk chosen to quote is a code fence (a `chunk_id` ending in `-code`), return that fence verbatim, with its line breaks and closing ```, instead of picking the 2 best-covering lines or sentences out of it. Nothing else changes: not the retriever, not the gates, not which chunk gets chosen, and not the handling of prose or table chunks.

**How it will be measured (by 2026-09-28):** re-ask all 126 questions in `week5/traffic_questions.txt` through the changed pipeline. Then re-read the same 20 seeded questions and apply the same test used in open coding. An output counts in this mode if its code isn't a complete, line-broken fence that parses as Python.

**Expected numbers:**

1. **Mode 1 on the seeded 20: 2/20 (10%) → 0/20 (0%).** `tr-b292e79be2` and `tr-16c2469574` will both return the full `verify_signature(...)` block.
2. **Across all traffic: 9/126 (7.1%) outputs cite a `-code` chunk, and all 9 are mangled today → 0/126 mangled.** The same 9 questions will still cite the same `-code` chunk.
3. **Guardrails, which also count as wrong if they move:** the other **117/126 outputs are byte-identical** to `traces.jsonl`, and **refusals stay at exactly 46/126**.
4. **Side effect I expect:** mode 6 ("prints the same sentence twice") drops from **6/20 to 5/20**, because only `tr-b292e79be2` leaves it.
5. **What it will not fix:** mode 3 stays at **5/20**. `tr-16c2469574` will show the code but still won't say the scheme is `"v3"`.

If mode 1 doesn't reach 0/20, or any guardrail number moves, this prediction was wrong. The write-up will say so, together with the trace that broke it.
