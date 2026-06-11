#!/bin/bash
# Run a baseline method from the paper.
#
# Baselines are simple reference methods the paper compares against. 
# Implement this only if applicable, i.e. the paper has baselines.
# You do not need to implement all baselines to begin — 
# just enough to validate that the evaluation pipeline works 
# and provide a reference point. You can decide to expand more baselines later.
# Each baseline must be actually run and scored through evaluate.sh
# so the numbers are verified, not self-reported.
# You can decide what this baseline script should do yourself.
#
# Usage:
#   bash scripts/baseline.sh [refpol|pomcp]

set -e

cd /home/user

EPISODES="${EPISODES:-24}"
SIMULATIONS="${SIMULATIONS:-350}"
PARTICLES="${PARTICLES:-100}"
MAX_STEPS="${MAX_STEPS:-40}"
SCENARIO="${SCENARIO:-default}"
NAME="${1:-refpol}"

mkdir -p checkpoints
case "$NAME" in
  refpol)
    SEED="${SEED:-1007}"
    python -m baseline.refpol \
      --episodes "$EPISODES" \
      --particles "$PARTICLES" \
      --max-steps "$MAX_STEPS" \
      --seed "$SEED" \
      --scenario "$SCENARIO" \
      --out "${OUT:-checkpoints/refpol_episodes.jsonl}"
    ;;
  pomcp)
    SEED="${SEED:-2007}"
    python -m baseline.pomcp \
      --episodes "$EPISODES" \
      --simulations "$SIMULATIONS" \
      --particles "$PARTICLES" \
      --max-steps "$MAX_STEPS" \
      --seed "$SEED" \
      --scenario "$SCENARIO" \
      --out "${OUT:-checkpoints/pomcp_episodes.jsonl}"
    ;;
  *)
    echo "Unknown baseline: $NAME" >&2
    exit 2
    ;;
esac

if [ "${RUN_EVAL:-1}" = "1" ]; then
  bash scripts/evaluate.sh
fi
