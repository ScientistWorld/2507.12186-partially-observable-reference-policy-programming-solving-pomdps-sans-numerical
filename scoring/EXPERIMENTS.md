# Experiment Overview

## scaled_maze_online_planning

This experiment tests whether a planner improves over a heuristic-only policy
on a partially observable navigation task with sparse observations, delayed
goal reward, and unsafe routes. It is the accessible reproduction benchmark for
the paper's central claim: online planning should turn useful but imperfect
candidate actions into a stronger policy than executing those candidates
directly.

The official reproduction script also records a POMCP-style tree-search
baseline with fixed directional macro actions on the same episode format. This
gives future agents a second comparison point in addition to the heuristic-only
reference policy.

The primary metric is a relational claim check: a run scores 1 only if the
planner beats every available baseline on both success rate and mean total
reward. Raw success, reward, standard error, and baseline-gap metrics remain in
`scores.json` for diagnosis and optimization.
