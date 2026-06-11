# Research Direction

## Research Problem

The benchmark studies online planning for long-horizon POMDP navigation with
continuous states, macro actions, sparse observations, delayed rewards, and
limited planning computation per executed action.

## Core Contribution

Work should improve online belief-space planning that evaluates candidate
macro actions with simulated futures before each executed action. The point is
to make imperfect domain heuristics useful without simply executing them
directly.

## Approach Scope

In-bounds changes include better tree search rules, belief-state management,
candidate-action generation, rollout/value estimation, and planning-time
allocation, provided the planner remains an online POMDP planner using the same
environment and evaluation artifacts.

## Out of Bounds

- Replacing the task with a fully observable shortest-path problem.
- Hardcoding action sequences for the fixed map or seed set.
- Using external training data or offline supervised policies tailored to the
  evaluation episodes.
- Changing the reward function, observation model, or transition model to make
  the task easier.
