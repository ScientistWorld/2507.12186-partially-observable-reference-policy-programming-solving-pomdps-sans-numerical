# Hardening checks (final iteration)

- `agents.py`: honest variants, search-free policies, exhaustive search and shortcut agents. Each is selected with `--kind`; manifests are in `manifests/`.
- `manifests_sabotage/`: the reference with crashing baselines.
- `run_checks.sh`: runs every case through `eval/test/evaluate.py` into `results/` (job `48547e3f-053`, final code, 300 hidden layouts). Finished cases are skipped on rerun.
- `analyze.py`: rank deltas, paired comparisons and seed spread. Writes `results/summary.json`.
- `results_job1/`: the intermediate job `b741c670-caf` (200 layouts, fixed-simulation reference, per-step budget before the reference planned against the clock).

The rest of `redteam/` is the previous audit of the old artifact-based gym. It is kept as the "before" record; its executables target removed modules.
