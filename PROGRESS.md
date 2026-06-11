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
original benchmark tables. A local smoke test on the accessible scaled maze
with 12 episodes produced:

- PORPP: success rate 0.833, mean total reward 1152.3.
- RefPol: success rate 0.667, mean total reward 906.0.

These smoke-test numbers are preliminary; `scripts/run.sh` submits a larger
CPU reproduction job.

## Remaining

- Run the submitted reproduction job and inspect the full generated scores.
- If budget allows, add a second scaled setting or implement a POMCP macro-action baseline.

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
is not replaced.
