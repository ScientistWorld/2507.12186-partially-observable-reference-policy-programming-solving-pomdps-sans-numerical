#!/bin/bash
# Job entry point: reference reproduction, then the hardening checks
# (variants and shortcuts through the hidden-test evaluator).
set -euo pipefail
cd /home/user
mkdir -p redteam/hardening/results
if [ ! -s scoring/scores_test.json ] || [ ! -s redteam/hardening/results/episodes_test_reference.json ]; then
  bash scripts/reproduce.sh --episodes-out redteam/hardening/results/episodes_test_reference.json
fi
bash redteam/hardening/run_checks.sh
