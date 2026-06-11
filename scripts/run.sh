#!/bin/bash
# Example job script submitted via the end-of-turn YAML block.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available
#   - No internet access
#
# Make sure all data, code, and dependencies are already in the
# workspace or baked into the container before submitting.

set -e

cd /home/user

export EPISODES="${EPISODES:-32}"
export PARTICLES="${PARTICLES:-120}"
export MAX_STEPS="${MAX_STEPS:-40}"
export SIMULATIONS="${SIMULATIONS:-500}"

bash scripts/reproduce.sh
python validate.py --compare
