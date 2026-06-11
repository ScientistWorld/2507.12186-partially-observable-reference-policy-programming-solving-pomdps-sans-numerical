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
- **Baseline:** `pomcp` is a particle Monte Carlo tree-search baseline that enumerates fixed directional macro actions, matching the paper's POMCP protocol more closely than the domain-specific candidate sampler.
- **Run:** execute `scripts/reproduce.sh`, which writes episode artifacts for RefPol, POMCP, and the submitted planner, then run `scripts/evaluate.sh`.
