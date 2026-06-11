# Experiment Overview

## scaled_maze_online_planning

This experiment tests whether a planner improves over a heuristic-only policy
on a partially observable navigation task with sparse observations, delayed
goal reward, and unsafe routes. It is the accessible reproduction benchmark for
the paper's central claim: online planning should turn useful but imperfect
candidate actions into a stronger policy than executing those candidates
directly.

## scaled_maze_anytime_planning

This experiment tests whether giving the same planner more online simulation
budget improves behavior on matched episodes. It captures the paper's anytime
claim separately from the baseline-gap claim.
