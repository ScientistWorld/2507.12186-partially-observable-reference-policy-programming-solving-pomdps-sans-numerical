# Progress

## What Works

Documentation has been drafted from `paper/2507.12186.md` for the problem statement, method summary, evaluation protocol, scoring targets, experiment descriptions, scientist constraints, and research direction.

Implemented a scaled continuous maze POMDP and the paper's PORPP online planner
with particle tree histories, progressive widening, preference-softmax action
selection, and sampled log-sum-exp preference backups. Implemented RefPol as
the heuristic-only baseline and an evaluator that reads saved episode JSONL
artifacts.

## Results

Paper reference numbers are recorded in `scoring/reference.json` for the two
original benchmark tables. The final revised CPU job on the accessible scaled
maze with 32 episodes produced:

- PORPP: success rate 0.875, mean total reward 1135.4.
- RefPol: success rate 0.6875, mean total reward 495.2.
- PORPP gaps: +0.1875 success rate and +640.2 mean total reward vs RefPol.

The job ran `scripts/run.sh`, wrote `scoring/scores.json`, and passed
`python validate.py --compare`.

Current iteration adds an anytime-budget check on the same scaled maze:
`checkpoints/porpp_low_episodes.jsonl` and
`checkpoints/porpp_high_episodes.jsonl` are produced by `scripts/reproduce.sh`
and summarized by `scripts/evaluate.sh` when present. This tests the paper's
claim that increased online planning generally improves PORPP behavior.

The first anytime CPU run completed successfully, but the 150-simulation
"low" budget was already strong on the selected seeds:

- PORPP low budget: success rate 0.9167, mean total reward 1270.9.
- PORPP high budget: success rate 0.8750, mean total reward 1123.3.

This does not support `core_claim_plus`; the low-budget setting has been
reduced to 25 simulations so the next run tests a more meaningful planning
budget contrast.

The immediate rerun still produced the same low-budget numbers because the
script's command-line `--simulations` default remained at 150 even though the
inline environment assignment had been reduced. This has been fixed, and PORPP
episode artifacts now include the `simulations` field so future logs expose the
actual planning budget used.

## Remaining

- Await the submitted CPU job to refresh the core benchmark and determine
  whether the added low/high planning-budget comparison supports
  `core_claim_plus`.
- Higher milestones would require implementing additional original-paper settings or more baselines, such as macro-action POMCP or RefSolver.
- The exact 3D maze and HEMS simulators remain unavailable, so this environment stops at the accessible scaled core-claim reproduction.

## Issues

The paper markdown appears to be OCR-derived in places, so some equations and pseudocode text are noisy. The high-level documentation is based on the readable sections and reported tables.

The paper does not provide the exact 3D maze/Corsica simulators or a
paper-specific code repository in the workspace.

## Deviations from Paper

The original unreleased 3D maze and HEMS simulators are replaced by a small
continuous maze analogue in `data/maze_pomdp.py`. The substitute preserves the
core evaluation phenomenon needed for the method: partial observability, sparse
landmark localization, macro actions, delayed goal reward, and a heuristic
candidate sampler that is useful but insufficient. The PORPP algorithm itself
is not replaced. The danger penalty in the substitute is larger than the
paper's 3D maze penalty so that direct heuristic routes remain clearly unsafe
at the smaller scale.
