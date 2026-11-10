#!/bin/bash
set -euo pipefail
cd /home/user
for name in \
  reference_original reference_seed7 reference_seed1007 reference_seed2007 \
  better_budget_seed7 better_budget_seed1007 better_budget_seed2007 \
  better_candidate_search weaker_one_sim baseline_refpol bruteforce \
  shortcut_fabricated_success shortcut_failed_huge_reward \
  shortcut_baseline_sabotage shortcut_select_success shortcut_relabel_replay \
  shortcut_easier_environment shortcut_missing_method shortcut_unlisted_method \
  shortcut_score_prewrite shortcut_empty shortcut_invalid_numbers \
  shortcut_constant_goal shortcut_fixed_map; do
  echo "Running audit case: $name"
  bash "redteam/$name/run.sh" || echo "FAILED audit case: $name"
done
python -m redteam.analyze
