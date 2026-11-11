# Scientist Constraints

## Task and evaluation

The evaluator (`eval/train/`, `eval/test/`) owns the dynamics, the noise, the layouts and the scoring. Do not modify `eval/`, and do not read `eval/test/` (hidden layouts, starts and noise seeds) from your method.

`data/maze2d.py` is a public model of the same task for planning. Editing it does not change how episodes are scored; it only changes your agent's model.

## Interface

Submit a method as an agent registered in `checkpoints/agents/<name>.json` that speaks the JSON-lines protocol in `briefing/evaluation.md`. Agents must:
- return 1–10 finite headings per decision;
- keep stdout for protocol messages.

## Compute

Planning is limited by the CPU allowance the evaluator announces in each `reset`. It is measured on the agent's whole process tree:
- per primitive step of the macro actions returned;
- separate allowances for start-up and per-instance preparation.

Offloading work to other processes, threads or reset-time precomputation is counted. Exceeding the allowance fails the episode. No GPU is available; there is one CPU per job.

## Data

There are no training sets beyond the public layouts in `eval/train/`. Methods may also generate their own layouts with `data/maze2d.generate_instance` for development or offline learning.

## Compliance checklist

- [ ] The agent is registered in `checkpoints/agents/` and runs through `scripts/evaluate_train.sh` without failures.
- [ ] `eval/` is unchanged, and the method never opens files under `eval/test/`.
- [ ] Episodes stay within the announced CPU allowance (see `_diagnostics.max_budget_fraction` in the score files).
- [ ] Results are compared with the reference on both experiments, using paired per-layout differences.
