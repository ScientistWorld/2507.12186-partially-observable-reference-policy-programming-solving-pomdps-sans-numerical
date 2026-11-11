#!/bin/bash
# Job entry point: reproduce the reference results end to end (CPU only).
# Writes scoring/scores_train.json, scoring/scores.json and
# scoring/scores_test.json for every agent in checkpoints/agents/.
# The hardening checks (variants and shortcuts through the hidden-test
# evaluator) are in redteam/hardening/run_checks.sh.
set -euo pipefail
cd /home/user
bash scripts/reproduce.sh
