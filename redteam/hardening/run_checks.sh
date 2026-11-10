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
# cheap shortcuts first
for k in shortcut_crash shortcut_fabricate shortcut_nan_output shortcut_huge_macro goal_direct localise_then_goal; do
  run_case "$k" "$M"
done
# honest variants (full hidden test)
for k in porpp_one_sim porpp_seed1 porpp_seed2 porpp_safe_sampler porpp_mixed_sampler ucb_candidates porpp_deep \
         bruteforce_sequences porpp_more_sims_1_8x shortcut_easier_model porpp_private_search_4x; do
  run_case "$k" "$M"
done
# expensive shortcuts that fail on every episode: 40 instances are enough
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

# Baselines replaced by crashing agents: the candidate's scores must not move.
if [ ! -s "$OUT/baseline_sabotage.json" ]; then
  python -m eval.test.evaluate --agents-dir redteam/hardening/manifests_sabotage --out "$OUT/baseline_sabotage.json"
fi
rm -f checkpoints/fabricated_episodes.jsonl tmp/fabricated_scores_*.json
echo "hardening checks done $(date +%T)"
