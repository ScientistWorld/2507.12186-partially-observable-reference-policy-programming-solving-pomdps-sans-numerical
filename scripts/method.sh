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
SCENARIO="${SCENARIO:-default}"
OUT="${OUT:-checkpoints/porpp_episodes.jsonl}"

mkdir -p checkpoints
python -m method.porpp \
  --episodes "$EPISODES" \
  --simulations "$SIMULATIONS" \
  --particles "$PARTICLES" \
  --max-steps "$MAX_STEPS" \
  --seed "$SEED" \
  --scenario "$SCENARIO" \
  --out "$OUT"

if [ "${RUN_EVAL:-1}" = "1" ]; then
  bash scripts/evaluate.sh
fi
