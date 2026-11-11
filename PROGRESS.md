# Progress

## Current state (final hardening iteration)

The gym evaluates **online planners as agents**. `eval/train/evaluate.py` and `eval/test/evaluate.py` are independent copies with their own dynamics (`maze_env.py`) and instance files. Each one:
- starts every agent registered in `checkpoints/agents/*.json`;
- sends it public maze layouts;
- executes its macro actions with evaluator-owned noise;
- enforces a calibrated CPU planning budget;
- computes `success_rate`, `mean_return` and `collision_rate` for `maze_standard_budget` (weight 0.6) and `maze_tight_budget` (weight 0.4).

Test results (300 hidden layouts):

| Agent | Standard success / return / collision | Tight success / return / collision |
|---|---|---|
| PORPP (`method/porpp.py`) | 0.850 / 781.3 / 0.150 | 0.703 / 538.9 / 0.297 |
| RefPol (`baseline/refpol.py`) | 0.233 / −215.8 / 0.747 | 0.270 / −194.6 / 0.713 |
| POMCP (`baseline/pomcp.py`) | 0.010 / −426.9 / 0.000 | 0.027 / −414.2 / 0.043 |

On train (100 public layouts) PORPP scores 0.91 / 0.67 in `scores_train.json`. A second, time-based pass for `scores.json` gave 0.88 / 0.70.

Verification of variants and shortcuts: `HARDENING.md` and `redteam/hardening/`.

## Reproduce

- `bash scripts/run.sh` (= `scripts/reproduce.sh`; CPU only, about 65 min on one core).
- `bash redteam/hardening/run_checks.sh` reruns the hardening cases.
- `python -m redteam.hardening.analyze` summarises them.

## Deviations from the paper

- The original 3D-maze and HEMS simulators are unreleased. The gym uses a 2D, procedurally generated stand-in for the 3D maze (44×30 cells, routes of 30–60 steps, 200-step horizon). The paper's dimension-free settings are kept.
- The probabilistic roadmap is a lattice roadmap with 0.7 units of danger clearance.
- Wall-clock planning time is replaced by a calibrated CPU allowance per primitive step. PORPP plans until 75% of it is used.
- PORPP settings the paper leaves open: η = 0.02, κ = 2, α = 0.5, D_max = 50, 200 root particles, new-child preference = node value.
- RefSolver and the HEMS experiment are not implemented.
