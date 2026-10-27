# Top 3 known weaknesses, written before anyone asked

**Written 2026-10-27 (Tuesday), after the first full eval runs and before the fresh-eyes review or the demo.** The
brief asks for Wednesday. These were written a day early, on the day they were found, and have not been softened
since.

## 1. The verification spiral: it says "I don't know" to 12% of answerable questions

4 of 33 r2_b questions (C16, C21, C23, C24; 3 of 32 in r2_a, different cases) end in "I don't know" although a tool
result in the same trace contains the answer. The agent keeps checking names it already has (`Client`, `file_path`,
`TooManyRequestsError.response`) with `symbol_exists` / `check_deprecation` until the 8-lap budget runs out.
`tr-008ab778c2af` has `page_size` in lap 1 and gives up at lap 8. This is the price of the fix that took wrong-version
code to 0: the "never invent a signature" rule plus a symbol checker made the agent unable to decide it is done. Each
spiral costs 1.7x a good answer ($0.0049 vs $0.0028) and takes 37 s.
**Not fixed.** Planned fix (ranked first in `cost_and_10x.md`): the host caps verification calls at 3 per question,
and on lap 7 the host tells the model "final answer now, with what you have". The code check is the backstop if that
produces an invented name.

## 2. Wrong-version code is at 0/19, but most of that 0 comes from the prompt, which nothing enforces in code

The move from 37.5% to 0% came almost entirely from r0 → r1: the version-aware prompt and the Week 12 tool
descriptions. In r2 the deterministic guards hardly fired. The version pin rewrote 2 calls, the code-check repair
fired 0 times, and 0 citations were dropped. So if the model drifts or someone edits the prompt, the guards are
untested against live failures; they are proven only by unit tests with a fake model. On top of that, the symbol
table checks names, not behaviour: `Client(timeout_ms=120)` (meant: 2 minutes) passes, `page.items` is never checked,
and nothing executes the code against a real SDK. n=19 answers with code gives a 95% upper bound of 16.8% on the
true rate.

## 3. In-IDE it is too slow and too token-hungry: p95 39 s, and ~21k input tokens per question

p50 23.8 s and p95 38.6 s per question (r2_b), 99.6% of it in LLM laps. Each lap is a `claude -p` subprocess
(215 MB RSS, ~1.5 s start-up) that re-sends a ~3.8k-token prompt, 5.6 laps per question. That is already
unacceptable for an IDE assistant at today's traffic, and at 9,000 integrators the input-token rate limit is the
first thing that breaks (`cost_and_10x.md`). The judge agreement (93.9%) is also against labels Claude wrote, not a
human. It is honest as far as it goes, but it is not the human-agreement number the rubric means until a person
relabels the 33 answers.
