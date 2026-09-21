# Failure taxonomy: SDK docs assistant, 20 random traces (seed 20260921, 2026-09-21)

The modes were clustered from the 20 open-coding sentences in `notes.md`. A trace can show more than one mode, so the percentages don't add up to 100%. 17 of 20 traces show at least one mode, and 3 are clean. Ranking uses severity first, then count.

| Rank | Failure mode (what a user sees) | Count | % of 20 | Severity | Example | All traces |
|---|---|---|---|---|---|---|
| 1 | **Code sample comes back squashed onto one line or cut off mid-call** (`verify_signature(`), so it can't be pasted and run | 2 | 10% | **Ships broken code to a user's repo** | `tr-16c2469574` | 18, 19 |
| 2 | **Describes a v2-only API as if it still exists, with no "removed in v3" warning**, even when that warning was retrieved | 1 | 5% | **Ships broken code to a user's repo** | `tr-16cdcfb0f1` | 05 |
| 3 | **Quotes the sentence next to the fact instead of the fact** (no default value, no yes/no, no `body=`), even though the fact is in the top 3 | 5 | 25% | Merely annoys: a dead end, so the reader has to go to the docs | `tr-4e8ace72b2` | 02, 03, 10, 13, 19 |
| 4 | **Says "I don't know" while a retrieved top-3 chunk states the answer** | 3 | 15% | Merely annoys: a dead end | `tr-4fc7b3e2f0` | 07, 15, 17 |
| 5 | **Fetches chunks about a different topic** (429 rate-limit text for a webhook-retry question, the changelog intro instead of its sections), **then says "I don't know"** | 3 | 15% | Merely annoys: a dead end | `tr-b533926bc3` | 08, 14, 20 |
| 6 | **Prints the same sentence twice in one answer** | 6 | 30% | Merely annoys: cosmetic, content still right | `tr-e144a5320d` | 01, 09, 11, 13, 16, 18 |

**Read-across:** 6/20 (30%) of answerable questions end in "I don't know" (modes 4 and 5 together). Code that can't be run or no longer exists reaches the user in 3/20 (15%) of traces (modes 1 and 2).

**Next week's target: mode 1.** It is the highest-severity mode and the most frequent of the "ships broken code" modes. See `prediction.md`.
