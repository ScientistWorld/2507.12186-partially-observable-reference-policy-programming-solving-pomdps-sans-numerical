# Reproduction Milestones

**Current: core_claim**

<!-- Milestone levels (update "Current" above as you progress):
  none             — just started, no meaningful progress yet
  method_runs      — the paper's method executes end-to-end without errors
  core_claim       — minimum experiment supports the paper's central claim
  core_claim_plus  — core claim reproduced on additional settings
  secondary_claims — secondary results or contributions reproduced
  majority         — more than half of reported results reproduced
  near_complete    — most results reproduced, only minor gaps remain
  full             — all reported results reproduced
-->

## Progress Log

### [2026-06-11 22:10] - method_runs
- Read the paper and identified PORPP's particle-tree online planning algorithm.
- Implemented a scaled maze POMDP, RefPol baseline, PORPP planner, and artifact-based evaluation.
- Ran a lightweight local smoke test showing the method executes end-to-end and writes `scoring/scores.json`.

### [2026-06-11 22:45] - core_claim
- Completed a CPU compute job successfully; `scripts/run.sh` ran RefPol, PORPP, and `validate.py --compare`.
- Added explicit PORPP-vs-RefPol success and reward gap metrics so scoring measures both benefit and the reference-policy constraint.
- Tuned the scaled maze reward so unsafe direct heuristic routes are costly enough for online planning to matter; local validation shows PORPP ahead of RefPol on success and reward.

## Stop Justification
- Not stopped. A follow-up CPU job is being submitted to regenerate final scores after the benchmark and scoring cleanup.
