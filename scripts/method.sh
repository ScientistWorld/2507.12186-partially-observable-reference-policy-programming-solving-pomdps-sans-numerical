#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

EPISODES="${EPISODES:-24}"
SIMULATIONS="${SIMULATIONS:-350}"
PARTICLES="${PARTICLES:-100}"
MAX_STEPS="${MAX_STEPS:-40}"
SEED="${SEED:-7}"

mkdir -p checkpoints
python -m method.porpp \
  --episodes "$EPISODES" \
  --simulations "$SIMULATIONS" \
  --particles "$PARTICLES" \
  --max-steps "$MAX_STEPS" \
  --seed "$SEED" \
  --out checkpoints/porpp_episodes.jsonl

bash scripts/evaluate.sh
