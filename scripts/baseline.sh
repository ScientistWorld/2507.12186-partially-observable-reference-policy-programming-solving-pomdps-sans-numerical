#!/bin/bash
# Run a paper baseline through the evaluator on the visible instances.
# Usage: bash scripts/baseline.sh [refpol|pomcp]
set -e
cd /home/user
export PYTHONPATH=/home/user
NAME="${1:-refpol}"
shift || true
mkdir -p tmp
python -m eval.train.evaluate --only "$NAME" --out "tmp/scores_${NAME}_train.json" "$@"
