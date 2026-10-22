# Week 9 Task Set E: adding the package-registry server without touching the agent

**Host (the agent, where the model runs):** `week9_agent.py`

**Server one (ours):** `week9_docs_server.py` (docs-search)

**Server two (DevRel's, vendored):** `week9/vendor/package_registry/server.py`

**Model:** Claude Haiku 4.5 through the headless `claude` CLI, the same `call_llm` as Weeks 7–8.

**MCP SDK:** `mcp` 1.30 (FastMCP), pinned `<2` because 2.x renamed FastMCP.

## Submission checklist

| Deliverable | File | Result |
|---|---|---|
| Agent module unchanged | `agent_diff.txt` | **0 lines changed**: empty `git diff --stat`, identical sha256, and the same `agent_module_sha256` logged by every run before and after |
| Config diff adding server two | `config_diff.txt` | +8 lines in `mcp_config.json`, nothing else |
| Raw initialize → tools/list → tools/call, annotated | `wire.json` (byte-exact copy in `wire_raw.jsonl`) | 7 messages; every top-level field annotated; model-call location stated |
| Tool count from tools/list | `tool_counts.txt` (from `tools_list_*.json`) | **3 before → 6 after** |
| Docstring-as-prompt + recoverable error | `error_before_after.md` | same failing call: retried v3 and gave working code **0/3 → 3/3** |
| Supply-chain risk note | `risk_note.md` | exactly 5 lines; verdict: ship only pinned, read-only, behind the gateway |

## 1. Config-only addition (requirements 1–3)

`./week9/run_sequence.sh` runs the whole thing:
1. Start with server one in `week9/mcp_config.json`.
2. Snapshot the agent module.
3. Run two queries.
4. Make the one config edit.
5. Run the same queries again.
6. Write `agent_diff.txt` and `config_diff.txt`.

The agent connects to every server in the config and runs `initialize` → `tools/list` (→ `resources/list` + `resources/read`) on each. It builds the model's tool list from what comes back. `tests/test_week9_mcp.py` asserts that no tool or server name appears anywhere in `week9_agent.py`.

**Proof the new server was called:** `logs/server1_plus_2_registry_query.jsonl`, lap 1: `"tool": "get_package_versions", "server": "package-registry"`.

**Tool count, from tools/list:**
- **3 before:** `search_docs`, `get_openapi_spec`, `check_deprecation`
- **6 after:** those 3 plus `get_package_versions`, `get_release_info`, `get_deprecation_notices`

**Same question, before and after:** *"We pin acme-sdk==2.9.4 … which release should we pin, when was it released, what does the constructor become?"*

| | laps | tokens | cost | answer |
|---|---|---|---|---|
| server one only | 8 | 27,159 | $0.0458 | right constructor; **no release date** ("check PyPI"); 6 `search_docs` calls looking for dates the docs don't contain |
| server one + two | 3 | 8,373 | $0.0121 | `3.2.0, released 2026-08-18` + `timeout_ms=30000`; 1 registry call, 1 docs call |

**Why there's a snapshot instead of a commit:** nothing for Week 9 is committed yet. So the "before" agent is a file snapshot (`snapshots/server1/`), and the diff uses `git diff --no-index`. The sha256 that each run logs at startup ties the runs to the exact file. If you commit the server-one state first and the config edit second, `git diff HEAD~1 -- week2Task/week9_agent.py` gives the same empty result.

**Being honest about the timeline:** the first attempt at this sequence found two host bugs:
- a reply carrying two JSON objects was rejected;
- the Week 7 "bare output contract" fallback was missing from the port.

Those bugs came from porting the loop, not from adding server two, so I fixed the agent and **redid the whole sequence from server one**. The diff shown is from the clean re-run.

## 2. Where the model runs (requirement 4)

> The model is called only in the host (`week9_agent.py` → `call_llm` → `claude` CLI), between `tools/list` and `tools/call`, where it picks a tool and its arguments. It is never called inside either MCP server or anywhere on the wire: the servers run plain code on the arguments they are sent and never see a prompt or a model.

Neither server imports an LLM client, and the version-support matrix is a **resource** (`docs://version-support-matrix`), not a tool. The host reads it once and attaches it to the system prompt, so no turn is spent fetching it. Section 5 of `error_before_after.md` shows that this resource alone kept the model from making the v4 call in free runs.

Two findings came straight from reading the wire:
- `serverInfo.version` is the SDK version (`1.30.0`), not the server's own version (`0.4.1`), so the handshake can't identify the build.
- FastMCP declares `prompts` and `resources` capabilities even when the server has neither.

## 3. Recoverable error (requirement 5)

The full write-up is `error_before_after.md`.

`search_docs` changed from `"Search the docs."` + `"Error 3"` to a prompt-style docstring plus an error that says three things: it's a missing version and not an outage, which versions exist, and the exact next call.

With lap 1 forced to the same failing call:

| | retried with v3 | correct v3 code |
|---|---|---|
| before | 0/3 (gave up, empty code) | 0/3 |
| after | 3/3 | 3/3 (`client.files.upload(file_path="report.pdf")`) |

Each fixed run costs one extra lap, about $0.004.

What it did **not** fix: in free runs with the new docstring, the model avoided the failing call but answered "want the v3 version?" with empty code (0/3). That is reported in the write-up rather than hidden.

## 4. Bonus: one front door, an audit line, a scoped token

`week9_gateway.py` is a single MCP server that is itself a client of both upstreams. The agent reaches it through `configs/gateway.json`, again with no agent change:
- It discovers 6 tools, all routed through `gateway`.
- Every `tools/call` writes one line to `logs/gateway_audit.log`:

```json
{"ts": "2026-10-05T08:21:43Z", "caller": "docs-assistant", "tool": "get_deprecation_notices", "requested": "acme-sdk@3.2", "server": "package-registry", "decision": "denied"}
{"ts": "2026-10-05T08:21:48Z", "caller": "docs-assistant", "tool": "get_package_versions", "requested": "acme-sdk@*", "server": "package-registry", "decision": "allowed", "isError": false}
```

**How the token scope works:**
- `gateway_scopes.json` is keyed by sha256(token), so the plaintext token isn't stored there.
- The `docs-assistant` token is denied `get_deprecation_notices`. Version lookup (`get_package_versions`, `get_release_info`) still works.
- An unknown token is denied everything.

**The denial reaches the model** as `isError: true` with this text: *"denied: … permission decision by the gateway, not an outage and not a missing package or version, so retrying will not help. Tools this caller may use: [...]"*

**Results:** see `gateway_demo_stdout.txt` and `logs/gateway_{seeded,free}_r*.jsonl`.
- In 4 of 4 runs (2 forced, 2 free), the model got the denial, did **not** retry the denied tool, and switched to `get_package_versions` + `check_deprecation`.
- All 4 answers were correct: 3.2.0 / 2026-08-18 / `timeout_ms=30000`.
- **What the denial cost:** none of the 4 answers mention that 3.2.0 removed the `timeout_s` shim (it now raises `TypeError`). Only the denied tool knows that.

## 5. Things found along the way

- **An answer without evidence.** In `logs/gateway_denial_run.jsonl` (the first gateway run, free), the model answered in lap 1 with **no tool call at all**. Its thought said "I found the deprecation notice showing timeout_s is removed". Nothing was found. MCP doesn't fix this; a trajectory check like Week 8's would catch it.
- **The third-party server's default access log** goes to `~/.cache/…`, outside the repo and never rotated. The config redirects it to `logs/registry_access.log`. The risk note covers what it records.
- **Server environment:** each server gets only PATH/HOME/USER/LOGNAME/SHELL/TERM plus its own config `env`, never the host's API keys. That limits leaks through env vars only: a stdio server still runs as our user and can read `.env` from disk.
- **Known nit, left unfixed:** `week9_agent.py` opens `/dev/null` for server stderr without closing it, which causes a ResourceWarning in the tests. Fixing it would change the agent module after the snapshot, so it stays until the next agent change.

## Run

```bash
.venv/bin/python -m pip install "mcp>=1.9,<2"
.venv/bin/python week9_agent.py --list-tools                                  # discovery only
.venv/bin/python week9_agent.py --qid Q01                                     # agent over MCP
./week9/run_sequence.sh                                                       # requirements 1-3 end to end
.venv/bin/python week9_wire.py                                                # raw JSON-RPC -> week9/wire_raw.jsonl
.venv/bin/python week9_error_experiment.py --reps 3                           # requirement 5
.venv/bin/python week9_agent.py --config week9/configs/gateway.json "..."     # bonus: through the gateway
.venv/bin/python week9_gateway_demo.py --reps 2                               # bonus: denial reaching the model
.venv/bin/python -m unittest tests.test_week9_mcp -v                          # 7 tests, no model calls
```
