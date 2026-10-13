Sunk-cost bias, named out loud: I just built the orchestrator, two workers and a hand-off log, and I want that work to count. That is not evidence, so this verdict ignores it.
Verdict: KILL the squad. Keep the single agent (week7_agent.py) for DevRel.
Pass rate: single 77% (23/30) vs squad 70% (21/30) on the same 10 Week-6 cases and the same judge. The squad did not win quality.
Latency: p50 16.9 s vs 43.1 s (2.5x slower), p99 39.5 s vs 71.7 s. The workers must run in sequence because code needs the version.
Bill: 117,861 vs 197,488 tokens per pass (1.7x multiplier), $0.0021 vs $0.0042 per question (2.0x).
The biggest hand-off (orchestrator -> version worker, 47% of squad tokens) hit its lap cap with no answer in 24/30 runs.
The squad's one clear win (E21, 2/3 vs 0/3) comes from the single agent running out of budget, not from the pattern itself.
When the version worker returned a 500, the squad didn't retry. It shipped an unchecked sample with a caveat (degraded, not a lie).
I did not re-run the squad after fixing the version worker's brief. "We tried it and it lost" is the result.
Multi-agent would earn a re-race only if the sub-tasks were independent enough to run in parallel; here they are not.
