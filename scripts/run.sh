#!/bin/bash
# Score the final method artifacts on the visible train slice and held-out test slice.

set -euo pipefail

cd /home/user

bash scripts/evaluate_train.sh /home/user/checkpoints
bash scripts/evaluate_test.sh /home/user/checkpoints
