# Evaluation Targets

## Primary: scaled_maze_online_planning

Tests whether an online planner can solve a poor-localization navigation POMDP
where a feasible-action heuristic alone is not reliable.

- **Metric:** `success_rate` (higher is better)
- **Metric:** `mean_total_reward` (higher is better)
- **Constraint metric:** `episodes` records the number of evaluated episodes and must remain comparable across methods.
- **Constraint metric:** `stderr_total_reward` should be reported so improvements are judged against run variability.
- **Run:** execute `scripts/reproduce.sh`, which writes episode artifacts for RefPol and the submitted planner, then run `scripts/evaluate.sh`.
