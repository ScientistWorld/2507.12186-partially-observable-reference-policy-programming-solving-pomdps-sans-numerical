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
original benchmark tables. A completed CPU job on the accessible scaled maze
with 32 episodes produced:

- PORPP: success rate 0.875, mean total reward 1270.4.
- RefPol: success rate 0.8125, mean total reward 1155.1.

After adding explicit gap metrics and increasing the scaled task's danger
penalty to make unsafe direct heuristic routes meaningfully costly, a local
16-episode validation run produced:

- PORPP: success rate 0.9375, mean total reward 1341.6, reward gap vs RefPol 431.1.
- RefPol: success rate 0.8125, mean total reward 910.5.

The next submitted job regenerates final scores for the revised benchmark.

## Remaining

- Run the submitted reproduction job for the revised benchmark and inspect the full generated scores.
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
is not replaced. The danger penalty in the substitute is larger than the
paper's 3D maze penalty so that direct heuristic routes remain clearly unsafe
at the smaller scale.
