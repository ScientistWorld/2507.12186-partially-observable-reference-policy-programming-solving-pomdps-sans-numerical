# Verification Report

## Initial Assessment

The workspace started at `core_claim` with a working scaled-maze reproduction
of the paper's central online POMDP-planning claim. The claimed milestone was
justified: PORPP artifacts beat both RefPol and directional POMCP on success
rate and mean return, and `python validate.py --compare` passed.

## Issues Found

- **Minor:** The default evaluator only scored the current named artifacts
  (`porpp`, `refpol`, `pomcp`) unless explicit paths were passed, which made
  `scripts/evaluate.sh` less reusable for future method artifacts.
- **Minor:** `scoring/TARGETS.md` named `core_claim_supported` as the primary
  metric, while `scoring/reference.json` correctly used the more graded
  `core_claim_margin_score`.
- **Minor:** The scaled substitute reference rows needed an explicit note that
  they are paper Table 1 scale anchors, not direct results from the substitute
  environment.
- **Cosmetic:** `scripts/evaluate.sh` still documented an obsolete
  method-name/checkpoint argument pattern.
- **Cosmetic:** Generated trajectory files were still tracked even though
  trajectory artifacts are ignored.

## Fixes Applied

- Updated `eval/evaluate_maze.py` to discover and score every
  `*_episodes.jsonl` artifact under the checkpoint directory, excluding the
  old low/high budget exploratory artifacts. Baselines remain identified by
  method key (`refpol`, `pomcp`); any other artifact is scored as a candidate
  planner.
- Regenerated `scoring/scores.json` from existing episode artifacts so baseline
  rows include `core_claim_supported: 0.0`.
- Aligned `scoring/TARGETS.md` with the actual primary metric
  `core_claim_margin_score`.
- Added a `notes` field to `scoring/reference.json` documenting the scaled
  substitute reference rows.
- Corrected `scripts/evaluate.sh` usage comments.
- Staged removal of generated tracked `trajectory/` JSONL files.

## Final Judgment

The workspace is ready to serve as a research gym for the accessible
scaled-maze version of the paper's core claim. Problem/data/eval separation is
clean: `eval/` does not import from `method/`, `data/` is method-independent,
and the evaluator reads method artifacts rather than regenerating the method.
The method-agnostic documents are suitable for from-scratch agents, and the
method documentation/code remain available for improve-mode agents.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: medium
- Key limitation: The original 3D maze and HEMS simulators were unavailable, so
  the gym uses a scaled continuous maze substitute rather than reproducing the
  full original benchmark suite.
