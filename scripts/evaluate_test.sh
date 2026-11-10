#!/bin/bash
# Held-out evaluation: runs every agent registered in checkpoints/agents/*.json
# on the hidden maze instances in eval/test/ (evaluator-owned rollouts under an
# enforced CPU planning budget) and writes scoring/scores_test.json.
# Takes no arguments; optional evaluator flags (e.g. --episodes-out FILE) are
# passed through.
set -e
cd /home/user
export PYTHONPATH=/home/user
mkdir -p scoring
python -m eval.test.evaluate "$@"
