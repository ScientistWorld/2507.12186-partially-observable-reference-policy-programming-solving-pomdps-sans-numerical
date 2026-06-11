# Evaluation Targets

## Primary: scaled_maze_online_planning

Tests whether an online planner can solve a poor-localization navigation POMDP
where a feasible-action heuristic alone is not reliable.

- **Metric:** `success_rate` (higher is better)
- **Metric:** `mean_total_reward` (higher is better)
- **Constraint metric:** `success_gap_vs_refpol` (higher is better) measures improvement over the heuristic-only policy.
- **Constraint metric:** `reward_gap_vs_refpol` (higher is better) measures reward improvement over the heuristic-only policy.
- **Constraint metric:** `episodes` records the number of evaluated episodes and must remain comparable across methods.
- **Constraint metric:** `stderr_total_reward` should be reported so improvements are judged against run variability.
- **Run:** execute `scripts/reproduce.sh`, which writes episode artifacts for RefPol and the submitted planner, then run `scripts/evaluate.sh`.

## Additional: scaled_maze_anytime_planning

Tests whether the same planner benefits from a larger online simulation budget
on matched seeds.

- **Metric:** `success_gap_vs_low_budget` (higher is better)
- **Metric:** `reward_gap_vs_low_budget` (higher is better)
- **Constraint metric:** `episodes` records the matched evaluation count.
- **Run:** execute `scripts/reproduce.sh`; the evaluator includes this target
  when both low- and high-budget PORPP artifacts are present.
