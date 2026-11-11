# Evaluation Targets

Both experiments are scored on 300 hidden layouts (`bash scripts/evaluate_test.sh`). The same metrics are reported on 100 public layouts (`bash scripts/evaluate_train.sh`).

## Primary: maze_standard_budget (weight 0.6)

**Budget:** 8 calibration units of CPU per primitive step.

| Kind | Metric | Direction | Coefficient | Reference (test) |
|---|---|---|---:|---:|
| Primary | `success_rate` | higher | 1.0 | 0.850 |
| Metric | `mean_return` (discounted; range [−500, 2000)) | higher | 0.5 | 781.3 |
| Constraint | `collision_rate` (episodes ending in a danger zone) | lower | 0.25 | 0.150 |
| Constraint | planning budget (enforced, not a metric) | — | — | — |

Over-budget episodes are scored as failures with the worst value of every metric.

**Baselines** (test, success): RefPol 0.233, POMCP 0.010.

## Secondary: maze_tight_budget (weight 0.4)

**Budget:** 1.6 calibration units of CPU per primitive step, the anytime regime.

| Kind | Metric | Direction | Coefficient | Reference (test) |
|---|---|---|---:|---:|
| Primary | `success_rate` | higher | 1.0 | 0.703 |
| Metric | `mean_return` | higher | 0.5 | 538.9 |
| Constraint | `collision_rate` | lower | 0.25 | 0.297 |
| Constraint | planning budget (enforced, as above) | — | — | — |

**Baselines** (test, success): RefPol 0.270, POMCP 0.027.

## Noise

Across three seeds of the reference, test success varies by 0.027 (standard) and 0.020 (tight). Compare methods with paired per-layout differences; `--episodes-out` writes per-episode records.

## Paper anchors

The paper's tables (3D maze and HEMS, 100 runs each) are stored unchanged under `_paper_*` keys in `scoring/reference.json`. The reference rows hold the paper's success rates at the analogous planning times. Returns are not on this maze's scale.
