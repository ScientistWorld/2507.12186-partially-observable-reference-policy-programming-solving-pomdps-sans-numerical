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
  checkpoints/pomcp_episodes.jsonl \
  checkpoints/refpol_episodes.jsonl \
  checkpoints/mirrored_danger/porpp_episodes.jsonl \
  checkpoints/mirrored_danger/pomcp_episodes.jsonl \
  checkpoints/mirrored_danger/refpol_episodes.jsonl \
  scoring/scores.json

mkdir -p checkpoints/mirrored_danger

EPISODES="${EPISODES:-24}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-7}" \
RUN_EVAL=0 \
bash scripts/baseline.sh refpol

EPISODES="${EPISODES:-24}" \
SIMULATIONS="${POMCP_SIMULATIONS:-350}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
RUN_EVAL=0 \
bash scripts/baseline.sh pomcp

EPISODES="${EPISODES:-24}" \
SIMULATIONS="${SIMULATIONS:-350}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-7}" \
RUN_EVAL=0 \
bash scripts/method.sh

EPISODES="${EPISODES:-24}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-3007}" \
SCENARIO=mirrored_danger \
OUT=checkpoints/mirrored_danger/refpol_episodes.jsonl \
RUN_EVAL=0 \
bash scripts/baseline.sh refpol

EPISODES="${EPISODES:-24}" \
SIMULATIONS="${POMCP_SIMULATIONS:-350}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-4007}" \
SCENARIO=mirrored_danger \
OUT=checkpoints/mirrored_danger/pomcp_episodes.jsonl \
RUN_EVAL=0 \
bash scripts/baseline.sh pomcp

EPISODES="${EPISODES:-24}" \
SIMULATIONS="${SIMULATIONS:-350}" \
PARTICLES="${PARTICLES:-100}" \
MAX_STEPS="${MAX_STEPS:-40}" \
SEED="${SEED:-3007}" \
SCENARIO=mirrored_danger \
OUT=checkpoints/mirrored_danger/porpp_episodes.jsonl \
RUN_EVAL=0 \
bash scripts/method.sh

bash scripts/evaluate.sh
