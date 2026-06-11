# Evaluation Targets

These targets define what future scores should measure. They are high-level benchmark targets, not paper-result values.

## Primary: maze_navigation_performance

Tests whether a planner can solve the poor-localisation 3D maze under the paper's online planning conditions.

- **Metric:** `expected_total_reward` (higher is better)
- **Metric:** `success_rate` (higher is better)
- **Run:** evaluate the maze scenario over the fixed 100-episode seed set at each configured planning-time budget.

## Primary: hems_navigation_performance

Tests whether a planner can complete the Corsica helicopter emergency mission while reacting to evolving no-fly-zone penalties.

- **Metric:** `expected_total_reward` (higher is better)
- **Metric:** `success_rate` (higher is better)
- **Run:** evaluate the HEMS scenario over the fixed 100-episode seed set at each configured planning-time budget.

## Constraint: baseline_improvement

Tests whether gains exceed the matched online planning baselines and the reference-policy-only baseline, rather than only solving an easier version of the task.

- **Metric:** `reward_gap_vs_best_baseline` (higher is better)
- **Metric:** `success_gap_vs_best_baseline` (higher is better)
- **Run:** compare each submitted planner against RefPol, RefSolver, and POMCP under the same environment, seeds, discount factor, macro-action limits, and planning-time budgets.

## Constraint: heuristic_not_sufficient

Tests whether performance depends on online planning in addition to the domain heuristic that proposes feasible candidate actions.

- **Metric:** `reward_gap_vs_refpol` (higher is better)
- **Metric:** `success_gap_vs_refpol` (higher is better)
- **Run:** evaluate the submitted planner and the heuristic-only reference policy on the same episode seeds.

## Constraint: anytime_behavior

Tests whether additional planning time improves or maintains performance instead of producing unstable degradation.

- **Metric:** `reward_time_trend` (higher is better)
- **Metric:** `success_time_trend` (higher is better)
- **Run:** evaluate the same planner across the configured planning-time budgets and compute trend summaries separately for each environment.

## Ablation: long_horizon_robustness

Tests whether the planner succeeds on delayed-reward, long-horizon settings rather than only short or locally greedy navigation cases.

- **Metric:** `late_objective_success_rate` (higher is better)
- **Metric:** `catastrophe_rate` (lower is better)
- **Run:** evaluate success and failure modes on the full-horizon maze and HEMS tasks with their original reward delays and termination rules.
