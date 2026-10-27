# The 10-minute demo script (four parts, to the clock)

Setup before the clock starts: `cd week2Task`, a terminal at least 120 columns wide, `claude` logged in. Run
`.venv/bin/python capstone.py ask "warm up" --sdk-version 3.0` once so the first live answer doesn't pay the
model download. Everything below is also chained in `.venv/bin/python capstone.py demo`. Use the separate commands
live, so a failure on stage is visible and not buried.

## Part 1: a real run (0:00-2:30)

```bash
.venv/bin/python capstone.py ask "how do I paginate through all invoices" --sdk-version 2.4
```

Point at, in this order:
1. `version: SDK 2.4 -> docs v2, code must run on v2 (resolved from flag: --sdk-version 2.4)`. This is span s1,
   **before** any retrieval span.
2. The answer is `client.paginate_auto(...)`, v2 code. The v3 answer would be `list_after()`.
3. `Version notes (SDK 2.4): paginate_auto() works on 2.4, but was removed in 3.0 ...`. The deprecation nobody
   asked about, generated from the changelog.
4. `Sources: [SDK v2 2.0-2.9] [v2-pagination::paginate-auto::3-code](corpus/sdk_v2/pagination.md#paginate-auto)`.
   The citation names the version, and the link opens the page.
5. `Code checked against the SDK v2 symbol table: pass`.
6. The span table: every `mcp.tools/call` line shows `server span ... trace_id=tr-...`, the same id as the trace,
   and `trace id survived the MCP hop: True`.

Then the removed method:

```bash
.venv/bin/python capstone.py ask "how do I use client.request() to POST an invoice?" --sdk-version 3.0
```

The first sentence should read "`client.request()` no longer exists in SDK 3.0. Use `client.send()`". If the live
model words it differently, show the version note line, which is deterministic.

## Part 2: the failures we found (2:30-5:30)

```bash
.venv/bin/python capstone.py trace tr-df2fb1813299 --brief     # Tuesday's wiring: v2.4 caller got v3 list_after()
```

- "This is r0, the parts as they stood on Tuesday. The 2.4 caller got v3 code: `client.list_after()` and
  `/v3/invoices`. It parses and imports cleanly, and it fails at runtime. 12 of 32 answers were like this (37.5%).
  The cause is a seam: Week 9's prompt says 'you answer with v3 code'. Also look at the bottom line: 0 server spans.
  The trace id died at the MCP hop."
- Open `week12/taxonomy.md`. Seven modes, frequencies, trace ids. **The mode integration created:** mode 2. The
  Week 11 redactor ran over the agent's code and turned `os.environ[...]` into `[REDACTED...]` (`tr-5871db30a290`).
  Neither part has that bug on its own.
- **The two other weaknesses written down before anyone asked** (`week12/weaknesses.md`): #1, the verification
  spiral, "I don't know" on 4 of 33, still open (`tr-008ab778c2af`). #3, p95 39 s and 21k input tokens per question.

## Part 3: a number that moved (5:30-7:30)

```bash
.venv/bin/python capstone.py compare
```

- "Wrong-version code samples: **37.5% → 0%**, 12 of 32 → 0 of 19 answers with code. For v2.4 callers alone, 11 of
  14 → 0 of 6. The 95% upper bound on that 0 is 17%."
- "The check is deterministic: parse, then every import, client method and keyword argument against the caller's
  symbol table. 10 of r0's 30 samples parsed fine and were still wrong. The LLM judge passed 2 of the 12 wrong ones."
- "Judge agreement on the integrated outputs: **31 of 33, 93.9%**, against labels locked before the judge ran. Both
  disagreements are the judge being stricter. The labels were written by Claude, not a human. That's in the report."
- **The one sentence:** "This suite does not run the code. The symbol table checks names, not behaviour, so
  `timeout_ms=120` for two minutes passes. And our corpus has none of the Stack Overflow answers, so we have no
  keep-or-drop hit-rate number at all."
- Say plainly: the prompt fix did most of the work. The code-level guards hardly fired with this model; they are the
  floor if it drifts.

## Part 4: what's next (7:30-10:00)

```bash
.venv/bin/python capstone.py loop      # ~1-2 min: RED under redaction policy v1, GREEN under v2, suite green, PII still redacted
```

- "The eval case that now permanently guards that failure is **C33**, plus a unit test that needs no model."
- "Cost per question: **$0.0031**, 100% LLM laps, 5.6 laps per question."
- "At 9,000 integrators in-IDE, the first thing that breaks is **input tokens per minute: 2.41M against a 2.0M
  limit at peak (121%)**. Then the $500 cap on working day 6. First fix: the spiral cap and pre-fetch to cut laps,
  then the SDK with prompt caching, which brings ITPM to about 36%." (`week12/cost_and_10x.md`)

If the loop's live C33 run happens to go green under v1 (the model didn't write `SECRET = os.environ[...]` this
time), say so: that is why the unit test, which is deterministic, is the real guard.
