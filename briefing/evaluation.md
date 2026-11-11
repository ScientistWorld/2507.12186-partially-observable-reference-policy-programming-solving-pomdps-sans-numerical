# Evaluation

## How a method is evaluated

A method is an **agent**: any command registered by a manifest `checkpoints/agents/<name>.json` of the form

```json
{"command": ["python", "-m", "my_package.my_agent"]}
```

The evaluator runs the agent inside its own rollouts. It never reads files the agent writes.

**Process and messages.** The evaluator starts the command with the workspace root as the working directory and on `PYTHONPATH`. One process serves consecutive episodes, and is restarted after any failure. The evaluator and the agent exchange one JSON object per line over stdin/stdout. Stdout is reserved for protocol messages; log to stderr.

```
evaluator -> {"type": "hello"}                                    agent -> {"type": "hello"}
evaluator -> {"type": "reset", "instance": {...}, "seed": int, "budget": {...}}
                                                                  agent -> {"type": "ready"}
evaluator -> {"type": "act", "step": t, "observations": null | [null | [x, y], ...]}
                                                                  agent -> {"type": "action", "headings": [h1, ..., hk]}   (1 <= k <= 10)
... until the episode ends ...
evaluator -> {"type": "end"}        (then another reset, or {"type": "shutdown"})
```

**What the agent receives:**
- `instance` is the public layout: `grid` (rows of `#`/`.`, row index = y), `starts`, `goals`, `dangers` and `landmarks` (each `[x, y, radius]`), and the task constants (`gamma`, rewards, `motion_noise_std`, `step_size`, `max_macro_len`, `horizon`).
- `observations` lists, for every primitive step of the previous macro action, either `null` or the observed position.
- `seed` is a fixed per-instance seed for the agent's own randomness.

**Helpers.** `data/agent_protocol.py` (`run_agent`, `PlanningClock`) implements the protocol loop and the budget arithmetic. `data/maze2d.py` provides a generative model of the task. Using them is optional.

**Who computes the outcome.** The evaluator executes the headings in its own copy of the dynamics, with its own noise stream, and decides success, return and collisions itself. On a given instance, every agent faces the same true start and the same per-step noise.

## Planning budget (enforced)

Like the paper, which compares planners at matched planning time, the evaluator limits computation. CPU time is measured on the agent's whole process tree, including threads and child processes.

| Phase | CPU allowance |
|---|---|
| Process start → `hello` | `startup_cpu_seconds` (imports only; the instance is not known yet) |
| `reset` → `ready` | `reset_cpu_seconds` (per-instance preparation) |
| `ready` → last action of the episode | `slack_seconds` + `cpu_seconds_per_step` × (sum of the lengths of the macro actions returned) |

All values are sent in `budget`. `cpu_seconds_per_step` is `units_per_step` times a machine unit, which the evaluator measures on the running machine. Exceeding any allowance, or not answering within the wall-clock safety timeouts, fails the episode.

## Experiments and metrics

Each experiment runs every registered agent on 300 hidden layouts (`eval/test/`, test) or 100 public layouts (`eval/train/`, train).

| Experiment | Budget | Weight |
|---|---|---:|
| `maze_standard_budget` | 8 units per primitive step | 0.6 |
| `maze_tight_budget` | 1.6 units per primitive step | 0.4 |

Scored metrics, per experiment and agent:

| Metric | Direction | Coefficient | Meaning |
|---|---|---:|---|
| `success_rate` (primary) | higher | 1.0 | fraction of episodes that reach a goal within the horizon |
| `mean_return` | higher | 0.5 | mean discounted return, in [−500, 2000) |
| `collision_rate` | lower | 0.25 | fraction of episodes that end in a danger zone |

**Failures.** A failed episode counts as unsuccessful, return −500 (the lowest possible), collision 1. Failures include a crash, malformed or non-finite output, a macro outside 1–10 steps, a timeout, or a budget violation. A registered agent that never runs gets these worst values on every episode.

**Ranking.** Methods are ranked by the coefficient-weighted improvement over the reference, with each metric normalised by its spread across attempts. `_diagnostics` in the score files (failure reasons, budget use) is not scored.

**Commands:**
- `bash scripts/evaluate.sh`: visible layouts → `scoring/scores.json`.
- `bash scripts/evaluate_train.sh`: visible layouts → `scoring/scores_train.json`.
- `bash scripts/evaluate_test.sh`: hidden layouts → `scoring/scores_test.json`.

Options for development runs:
- `--only <name>`: score a single agent.
- `--limit N`: quick partial run (not a valid score).
- `--episodes-out FILE`: write per-episode records.

## Paper reference numbers

The paper (100 runs per setting, planning time per decision in seconds) reports, for its 3D maze:

| Planner | Success | Expected total reward |
|---|---:|---:|
| Proposed planner, 1 s | 71% | 570.3 ± 183.5 |
| Proposed planner, 10 s | 88% | 873.4 ± 172.1 |
| Proposed planner, 15 s | 94% | 983.1 ± 168.0 |
| RefPol | 29% | −572.2 ± 231.1 |
| RefSolver, 10 s | 30% | −384.0 |
| POMCP, 10 s | 13% | −1897.5 |

For HEMS, the proposed planner reaches 90% success at 10 s; all baselines are at or below 28%.

These numbers come from different simulators. Success rates here are only loose anchors, and returns are not on this maze's scale. `scoring/reference.json` keeps the full tables under `_paper_*` keys.
