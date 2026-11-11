#!/bin/bash
# Reproduce the reference results end to end (CPU only, ~65 min on one core:
# ~13 min per visible-split pass, ~39 min for the hidden test, mostly POMCP).
#
# PORPP and the baselines need no training: each registered agent
# (checkpoints/agents/{porpp,refpol,pomcp}.json) plans online inside the
# evaluator's rollouts.  This writes
#   scoring/scores_train.json  (visible instances, eval/train/)
#   scoring/scores.json        (same view, standard entry point)
#   scoring/scores_test.json   (hidden instances, eval/test/)
set -e
cd /home/user
bash scripts/evaluate_train.sh
bash scripts/evaluate.sh
bash scripts/evaluate_test.sh "$@"
