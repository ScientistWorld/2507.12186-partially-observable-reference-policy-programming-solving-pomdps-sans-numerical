#!/bin/bash
# Standard evaluation entry point (visible instances): runs every agent
# registered in checkpoints/agents/*.json through the evaluator-owned maze
# rollouts in eval/train/ and writes scoring/scores.json.
#
# An agent is any command speaking the JSON-lines protocol described in
# briefing/evaluation.md; register it with a manifest
#   checkpoints/agents/<name>.json  ->  {"command": ["python", "-m", "my.module"]}
#
# Examples:
#   bash scripts/evaluate.sh                       # all registered agents
#   bash scripts/evaluate.sh --only porpp          # one agent
#   bash scripts/evaluate.sh --limit 10            # quick smoke run (not a score)
set -e
cd /home/user
export PYTHONPATH=/home/user
mkdir -p scoring
python -m eval.train.evaluate --out scoring/scores.json "$@"
