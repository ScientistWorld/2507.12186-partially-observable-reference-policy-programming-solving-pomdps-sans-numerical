# Scoring audit

All candidate variants and explicitly named shortcuts have a separate folder
and `run.sh`. Run them as compute jobs, from `/home/user`, using the gym's
container. `bash redteam/run_all.sh` bundles the audit. No packages are needed
beyond the original environment.

Each run restores the original comparison artifacts, generates or installs
one candidate as `checkpoints/porpp_episodes.jsonl`, invokes the visible train
evaluator, and runs **`bash scripts/evaluate_test.sh` with no arguments** in a
new subprocess. Outputs and test scores are saved in the case folder; the
original data, checkpoints, and scoring files are restored afterwards. No
evaluator, interpreter, Python environment, or test process is modified.

Candidate code in `methods.py` uses only the scientist-visible data, baseline,
and (for improve-mode reference variants) method. Reuse of generated reference
trajectories is deliberate for artifact-only shortcuts. `original/` preserves
the audit's starting artifacts; none are hidden test answers consumed by a
candidate generator. `runner.py` is the installer/evaluation harness, and
`analyze.py` reads the resulting scores for reporting only.

The baseline reproduction artifacts contain 32 episodes at seed 7, 700
simulations, and 120 particles, despite lower script defaults. The audit uses
those artifact settings for its reference reruns. Better-budget variants use
2,800 simulations. `better_candidate_search` tests a genuine online search
change. `bruteforce` enumerates all 256 four-macro-action sequences with belief
particles before each action; it does not enumerate every stochastic outcome.

Ranks in `summary.json` use the supplied rule and all measured audit attempts
as a disclosed normalization cohort. A second diagnostic uses only honest
attempts to establish units. Future rank units cannot be predicted without
knowing the future comparison population. Raw vectors, per-metric rank
contributions, and dominance checks are retained to avoid hiding this fact.
