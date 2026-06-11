#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and should call
# scripts/baseline.sh and scripts/method.sh to run baselines and
# the paper's method, each of which calls scripts/evaluate.sh.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is /home/user
#
# This is the "gold standard" reproduction — 
# You do not need to run this, but keep this in good shape
# so other agents can easily run a full loop of reproduction and get the paper's numbers.

set -e

cd /home/user

rm -f \
  checkpoints/porpp_episodes.jsonl \
  checkpoints/porpp_low_episodes.jsonl \
  checkpoints/porpp_high_episodes.jsonl \
  checkpoints/refpol_episodes.jsonl \
  scoring/scores.json

EPISODES="${EPISODES:-24}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-7}" \
RUN_EVAL=0 \
bash scripts/baseline.sh

EPISODES="${EPISODES:-24}" \
SIMULATIONS="${SIMULATIONS:-350}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-7}" \
RUN_EVAL=0 \
bash scripts/method.sh

EPISODES="${ANYTIME_EPISODES:-24}" \
SIMULATIONS="${LOW_SIMULATIONS:-25}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-7}" \
RUN_EVAL=0 \
python -m method.porpp \
  --episodes "${ANYTIME_EPISODES:-24}" \
  --simulations "${LOW_SIMULATIONS:-150}" \
  --particles "${PARTICLES:-100}" \
  --max-steps "${MAX_STEPS:-40}" \
  --seed "${SEED:-7}" \
  --out checkpoints/porpp_low_episodes.jsonl

python -m method.porpp \
  --episodes "${ANYTIME_EPISODES:-24}" \
  --simulations "${HIGH_SIMULATIONS:-700}" \
  --particles "${PARTICLES:-100}" \
  --max-steps "${MAX_STEPS:-40}" \
  --seed "${SEED:-7}" \
  --out checkpoints/porpp_high_episodes.jsonl

bash scripts/evaluate.sh
