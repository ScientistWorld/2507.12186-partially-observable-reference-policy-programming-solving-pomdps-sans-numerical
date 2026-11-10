#!/bin/bash
# Visible-split evaluation: runs every agent registered in
# checkpoints/agents/*.json on the public maze instances in eval/train/ and
# writes scoring/scores_train.json.  Same protocol and budgets as the test.
set -e
cd /home/user
export PYTHONPATH=/home/user
mkdir -p scoring
python -m eval.train.evaluate "$@"
