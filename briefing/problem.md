# Problem Definition

This benchmark concerns online planning for long-horizon partially observable Markov decision processes (POMDPs) with continuous state and action spaces. An agent must choose actions from an uncertain belief state using a generative model, limited online planning time, and noisy or sparse observations.

## Research Question

Can an online POMDP planner solve long-horizon robotic navigation tasks with large continuous action spaces, sparse delayed rewards, partial observability, and dynamically changing hazards, while using only a small amount of planning time before each executed action?

The paper evaluates this question on two tasks:

- **3D maze with poor localisation:** a holonomic drone starts from one of two possible locations, receives position observations only at landmarks, and must reach a goal while avoiding danger zones.
- **HEMS mission with evolving no-fly zones:** a holonomic helicopter in a Corsica terrain model must visit two unordered victim locations while reacting to no-fly zones that appear at unknown fixed time steps.

## Why It Matters

Autonomous systems often need to plan under uncertainty with limited computation, especially when observations are incomplete and the environment changes during execution. Better online POMDP planning would enable safer and more reliable long-horizon decision making in robotics, rescue missions, and other uncertain control settings.

## Success Criteria

A successful solver should:

- Achieve high expected discounted total reward across repeated trials.
- Complete the navigation mission at a high success rate.
- Outperform strong online planning and reference-policy baselines under the same time budgets.
- Improve, or at least not degrade, as per-decision planning time increases.
- Remain effective when heuristic action proposals alone are not sufficient to solve the task.
