#!/bin/bash
# Regenerate method and baseline artifacts, then score the full, train, and
# held-out test views of the scaled maze benchmark.

set -euo pipefail

cd /home/user

EPISODES="${EPISODES:-32}" \
SIMULATIONS="${SIMULATIONS:-350}" \
POMCP_SIMULATIONS="${POMCP_SIMULATIONS:-350}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
bash scripts/reproduce.sh

bash scripts/evaluate_train.sh /home/user/checkpoints
bash scripts/evaluate_test.sh /home/user/checkpoints
