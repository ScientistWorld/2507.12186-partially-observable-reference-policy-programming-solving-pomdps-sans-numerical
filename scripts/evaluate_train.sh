#!/bin/bash
# Evaluate the visible train slice of the scaled maze benchmark.
#
# This mirrors scripts/evaluate.sh's artifact-scoring contract: methods write
# episode JSONL files under checkpoints/, and this script scores those files
# without importing or running method code.

set -e

cd /home/user

mkdir -p scoring

python -m eval.train.evaluate_maze "$@" --out scoring/scores_train.json
