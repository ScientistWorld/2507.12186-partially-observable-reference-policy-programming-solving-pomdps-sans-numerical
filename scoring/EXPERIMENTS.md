# Experiment Overview

The experiment names below are the intended keys for `scores.json` once implementation results are produced. They describe what each experiment establishes without revealing any solver internals.

## maze_navigation_performance

Evaluates overall task success in the poorly localized 3D maze. The experiment asks whether a planner can reason under ambiguous initial position, sparse localization feedback, danger-zone risk, and delayed goal reward within the paper's online planning-time limits.

## hems_navigation_performance

Evaluates overall task success in the Corsica helicopter mission. The experiment asks whether a planner can reach both unordered objectives while handling terrain constraints, noisy motion and observations, collision risk, and changing no-fly-zone penalties.

## baseline_improvement

Compares the evaluated planner with the standard reference and online-planning baselines under matched budgets and seeds. The purpose is to confirm that any improvement is meaningful relative to the baselines used to support the paper's central empirical claim.

## heuristic_not_sufficient

Checks whether the domain heuristic by itself is inadequate for solving the benchmark. This guards against treating the action-proposal mechanism or environment geometry alone as the full solution to the planning problem.

## anytime_behavior

Measures whether performance improves or remains stable as more online planning time is allowed before each executed action. This tests the practical anytime property expected from an online planner in these tasks.

## long_horizon_robustness

Measures whether the planner handles the full long-horizon versions of the tasks, including delayed objective rewards and costly failure modes. This prevents scores from being driven only by short-horizon local progress.
