# Progress

## What Works

Documentation has been drafted from `paper/2507.12186.md` for the problem statement, method summary, evaluation protocol, scoring targets, experiment descriptions, scientist constraints, and research direction.

## Results

No reproduction results have been generated yet. The documentation records the paper's reported target numbers for:

- 3D maze with poor localisation: success rate and expected total reward over 100 runs across 1, 2, 3, 5, 10, and 15 second planning budgets.
- HEMS mission with evolving no-fly zones: success rate and expected total reward over 100 runs across 1, 2, 3, 5, and 10 second planning budgets.

## Remaining

- Implement or verify benchmark environments.
- Implement the paper's online planning method and baselines.
- Create `scoring/reference.json` and `scoring/scores.json` with structures matching the documented targets.
- Run evaluation jobs for the paper method and baselines.
- Validate the workspace.

## Issues

The paper markdown appears to be OCR-derived in places, so some equations and pseudocode text are noisy. The high-level documentation is based on the readable sections and reported tables.

## Deviations from Paper

None yet. No method implementation or experiment has been run.
