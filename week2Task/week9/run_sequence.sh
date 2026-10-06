#!/usr/bin/env bash
# Week 9 Set E, requirements 1-3 end to end: server one -> config edit -> server one + two.
# The agent module is snapshotted while only server one is configured; after the config edit the agent is
# diffed against that snapshot. Nothing here edits week9_agent.py.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
Q="We pin acme-sdk==2.9.4 and construct the client with Client(timeout_s=30). Which acme-sdk release should we pin for the v3 migration, when was it released, and what does the constructor become?"

# --- server one only
cp week9/configs/server1.json week9/mcp_config.json
mkdir -p week9/snapshots/server1 && cp week9_agent.py week9/mcp_config.json week9/snapshots/server1/
$PY week9_agent.py --list-tools > week9/tools_list_server1.json
$PY week9_agent.py --qid Q01 --log week9/logs/server1_Q01.jsonl > /dev/null
$PY week9_agent.py --log week9/logs/server1_registry_query.jsonl "$Q" > /dev/null

# --- the ONLY change: add package-registry to the MCP config
cp week9/configs/server1_plus_2.json week9/mcp_config.json
$PY week9_agent.py --list-tools > week9/tools_list_server1_plus_2.json
$PY week9_agent.py --qid Q01 --log week9/logs/server1_plus_2_Q01.jsonl > /dev/null
$PY week9_agent.py --log week9/logs/server1_plus_2_registry_query.jsonl "$Q" > /dev/null

# --- the evidence
git diff --no-index week9/snapshots/server1/mcp_config.json week9/mcp_config.json > week9/config_diff.txt || true
{
  echo "Agent module = week9_agent.py. Baseline = week9/snapshots/server1/week9_agent.py, copied while week9/mcp_config.json held server one only."
  echo "Between the two states the only edit was week9/mcp_config.json (see config_diff.txt)."
  echo
  echo "\$ git diff --no-index --stat week9/snapshots/server1/week9_agent.py week9_agent.py"
  git diff --no-index --stat week9/snapshots/server1/week9_agent.py week9_agent.py && echo "(no output, exit 0: 0 lines changed)"
  echo "\$ git diff --no-index --numstat week9/snapshots/server1/week9_agent.py week9_agent.py | wc -l"
  git diff --no-index --numstat week9/snapshots/server1/week9_agent.py week9_agent.py | wc -l | tr -d ' '
  echo "\$ shasum -a 256 week9/snapshots/server1/week9_agent.py week9_agent.py"
  shasum -a 256 week9/snapshots/server1/week9_agent.py week9_agent.py
  echo
  echo "Runtime proof: each run logs sha256(week9_agent.py) and sha256(config) on its first line."
  for f in week9/logs/server1_Q01.jsonl week9/logs/server1_registry_query.jsonl week9/logs/server1_plus_2_Q01.jsonl week9/logs/server1_plus_2_registry_query.jsonl; do
    $PY -c "import json,sys; e=json.loads(open(sys.argv[1]).readline()); print(f'  {sys.argv[1]:<50} agent {e[\"agent_module_sha256\"][:16]}  config {e[\"config_sha256\"][:16]}')" "$f"
  done
} > week9/agent_diff.txt
cat week9/agent_diff.txt
