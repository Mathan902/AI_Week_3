# Ask Six Documents

A coursework RAG application that searches six synthetic documents. It uses dense embeddings and direct NumPy cosine similarity; it does not use a vector database.

## Features

- Six documents covering support, recipes, HR, insurance, SDK documentation, and contracts
- Two chunking configurations: 120/25 and 300/60 words
- `all-MiniLM-L6-v2` dense embeddings held in memory
- Top-K cosine-similarity retrieval with source metadata
- Configurable evidence threshold and an explicit “I don't know” response
- Source, section, chunk ID, and score shown for every retrieved result
- Side-by-side chunking comparison for each question
- Optional OpenAI grounded generation; an extractive fallback works without an API key

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The embedding model is downloaded the first time the app starts. To enable generated answers, set `OPENAI_API_KEY`. Without it, the app returns a short extract from the best-supported source.

## Test

```powershell
python -B -m unittest discover -s tests -v
```

## Demonstration

Use each prepared question in the app and show its cited source. Then select **Not in documents** and verify that the app refuses to answer. Compare the best retrieval score and source in the chunking comparison table. The documents are synthetic training material and should not be treated as real company policies or legal terms.

## Week 4: failure labelling and one retrieval change

```bash
.venv/bin/python week4_eval.py --retriever baseline   # dense + lexical boost (Week 3)
.venv/bin/python week4_eval.py --retriever hybrid     # + BM25 fused by RRF (k=60)
```

Each run scores hit-rate@3 on `golden_set.jsonl`, labels every failure R / G / Not-In-Corpus, measures p50 latency, and writes the inspection view to `week4_output/`. Results and the shipping decision are in `results.md`, and the code change is in `week4_change.diff`.

## Week 8: trajectory eval, the outcome-vs-trajectory gap, one mitigation

```bash
.venv/bin/python week8_trajectory_eval.py run --variant before   # Week 7 agent as shipped, 10 questions x 3
.venv/bin/python week8_trajectory_eval.py run --variant after    # with the one mitigation (argument validation) on
.venv/bin/python week8_trajectory_eval.py report                 # every table -> week8/report.md
.venv/bin/python -m unittest tests.test_week8_trajectory         # the path-set assertions, on fake runs
```

Each run is scored on the answer (Week 7 grader) and on the path: expected tool sequences asserted as sets of accepted paths, tool-choice accuracy, argument validity, step efficiency, and cost per question with p50 and max. The write-up, the named right-answer-wrong-path trace, the before/after count for the top mode with its price, the per-mode regression table and the injection bonus are in `week8/notes.md`; the mitigation is `week8/mitigation.diff`.

## Week 9: MCP, adding the package-registry server without touching the agent

```bash
.venv/bin/python week9_agent.py --list-tools        # initialize + tools/list against every server in week9/mcp_config.json
.venv/bin/python week9_agent.py --qid Q01           # the Week 7 loop with tools/call over MCP
./week9/run_sequence.sh                             # server one -> config edit -> server one + two, writes agent_diff.txt
.venv/bin/python -m unittest tests.test_week9_mcp   # discovery, config-only swap, recoverable error, gateway scopes
```

The agent (`week9_agent.py`) discovers every tool over MCP from a config file. Server one is our docs-search server (`week9_docs_server.py`); server two is DevRel's package-registry server, vendored in `week9/vendor/`. Adding it changed 0 lines of the agent and took tools from 3 to 6. The deliverables are `week9/agent_diff.txt`, `config_diff.txt`, `wire.json`, `tool_counts.txt`, `error_before_after.md` and `risk_note.md`. The write-up and numbers are in `week9/notes.md`; the bonus gateway is `week9_gateway.py`.

## Week 10: race the docs squad against the single agent

```bash
.venv/bin/python week10_race.py select                 # pick 10 of the 25 Week-6 cases once -> week10/cases.json
.venv/bin/python week10_race.py run                    # 10 cases x 3 repeats x {single, squad}, Week-6 judge_v2 + 8 assertions
.venv/bin/python week10_race.py failure --case E09     # version/deprecation worker returns HTTP 500
.venv/bin/python -m unittest tests.test_week10_squad   # hand-off logging, target version in the brief, injected 500 (fake LLM)
```

The squad (`week10_squad.py`) is an orchestrator with two narrow workers: version/deprecation, then code-sample. The single agent is the Week 7 loop. Both arms use the same model, tools, contract and judge. The deliverables are in `week10/`: `race_table.md`, `handoffs.log`, `multiplier.txt`, `failure_case.md`, `verdict.md` and `agent_card.json`. The write-up is `week10/notes.md`. Result: the squad costs 1.7x the tokens, runs 2.5x slower at p50 and has no pass-rate gain, so the verdict is KILL.
