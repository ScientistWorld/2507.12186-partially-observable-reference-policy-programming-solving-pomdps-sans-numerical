#!/bin/bash
# Evaluate the held-out test slice of the scaled maze benchmark.
#
# The test pass scores the same method entries found in scores_train.json when
# that file exists, using the complementary held-out episode partition.

set -e

cd /home/user

mkdir -p scoring

python -m eval.test.evaluate_maze "$@" --out scoring/scores_test.json
