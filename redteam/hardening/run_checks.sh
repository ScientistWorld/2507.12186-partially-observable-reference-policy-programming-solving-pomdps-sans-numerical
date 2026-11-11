#!/bin/bash
# Hardening checks: run honest variants and shortcut agents through the
# hidden-test evaluator (eval/test/evaluate.py, the code behind
# scripts/evaluate_test.sh).  Each case gets its own result file; finished
# cases are skipped so an interrupted job can resume.
set -uo pipefail
cd /home/user
export PYTHONPATH=/home/user
OUT=redteam/hardening/results
mkdir -p "$OUT"

run_case () {  # name agents_dir [extra args...]
  local name="$1"; local dir="$2"; shift 2
  if [ -s "$OUT/$name.json" ]; then echo "skip $name"; return; fi
  echo "=== $name $(date +%T)"
  python -m eval.test.evaluate --agents-dir "$dir" --only "$name" --out "$OUT/$name.tmp.json" \
      --episodes-out "$OUT/episodes_$name.json" "$@" && mv "$OUT/$name.tmp.json" "$OUT/$name.json"
}

M=redteam/hardening/manifests
# candidate improvements and reference noise first (the headroom question)
for k in porpp_plus porpp_stratified porpp_seed1 porpp_seed2 porpp_depth30 ucb_candidates porpp_fixed_sims; do
  run_case "$k" "$M"
done
# weaker policies, exhaustive enumeration, cheap shortcuts
for k in porpp_one_sim localise_then_goal goal_direct bruteforce_sequences shortcut_easier_model; do
  run_case "$k" "$M"
done
# shortcuts that fail on every episode: 100 instances are enough
for k in shortcut_crash shortcut_fabricate shortcut_nan_output shortcut_huge_macro; do
  run_case "$k" "$M" --limit 100
done
# private search beyond the allowance; process offload; reset-time planning
run_case porpp_private_search_3x "$M" --limit 100
for k in shortcut_reset_precompute shortcut_offload_process; do
  run_case "$k" "$M" --limit 40
done

# A name already reported on the visible split but with no agent on disk
# must receive the worst values rather than disappear from the test scores.
if [ ! -s "$OUT/shortcut_missing_method.json" ]; then
  cp scoring/scores_train.json "$OUT/scores_train.backup.json"
  python - <<'PY'
import json
p = "scoring/scores_train.json"
d = json.load(open(p))
for exp in d.values():
    if isinstance(exp, dict) and "results" in exp:
        exp["results"]["shortcut_missing_method"] = dict(next(iter(exp["results"].values())))
json.dump(d, open(p, "w"), indent=2)
PY
  python -m eval.test.evaluate --only shortcut_missing_method --out "$OUT/shortcut_missing_method.json"
  cp "$OUT/scores_train.backup.json" scoring/scores_train.json && rm "$OUT/scores_train.backup.json"
fi

# Baselines replaced by crashing agents: the candidate's scores must not depend on them.
if [ ! -s "$OUT/baseline_sabotage.json" ]; then
  python -m eval.test.evaluate --agents-dir redteam/hardening/manifests_sabotage --limit 100 \
      --out "$OUT/baseline_sabotage.json"
fi
rm -f checkpoints/fabricated_episodes.jsonl tmp/fabricated_scores_*.json
echo "hardening checks done $(date +%T)"
