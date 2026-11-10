#!/bin/bash
# Run the paper's method (PORPP, method/porpp.py) through the evaluator on the
# visible instances.  The agent is registered in checkpoints/agents/porpp.json;
# PORPP needs no training, so "running the method" is online planning inside
# the evaluator's rollouts.
set -e
cd /home/user
export PYTHONPATH=/home/user
mkdir -p tmp
python -m eval.train.evaluate --only porpp --out tmp/scores_porpp_train.json "$@"
