# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-11 21:55] - core_claim
- Verified the PORPP implementation runs end-to-end on the accessible scaled maze POMDP.
- Reproduced the central claim on the substitute benchmark: PORPP improves over the heuristic-only RefPol baseline in both success rate and total reward.
- Added a follow-up anytime-planning evaluation axis for low vs high simulation budgets.

### [2026-06-11 21:59] - core_claim
- Reran the corrected 25-vs-700 simulation budget check and confirmed the high-budget improvement is too small to support `core_claim_plus`.
- Cleaned the official scoring contract to the validated PORPP-vs-RefPol benchmark and regenerated `scoring/scores.json`.
- Verified `python validate.py --compare` passes.

## Stop Justification
- Completed at milestone `core_claim`.
