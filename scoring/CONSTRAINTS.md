# Scientist Constraints

These constraints define what future scientist agents must hold fixed when trying to improve scores in this benchmark.

## Problem Formulation

The scientist must solve the same online POMDP planning problem, with belief-state uncertainty, stochastic transitions, stochastic observations, and online planning before each executed macro action. Converting the tasks into fully observable shortest-path planning, using privileged true states at decision time, or solving a deterministic surrogate changes the problem and is not a valid improvement.

## Environments

The scientist must use the same two benchmark environments:

- 3D maze with poor localisation, two equally likely start positions, landmark-only exact localization observations, danger zones, goal reward, and step penalty.
- HEMS mission on the Cap Corse terrain, two unordered objectives, evolving no-fly zones at the paper's fixed but agent-unknown time steps, collision penalty, no-fly-zone step penalty, mission-completion bonus, and step penalty.

Changing map layouts, goal locations, reward values, transition noise, observation noise, termination rules, or no-fly-zone schedules would make results incomparable.

## Evaluation Budget

The scientist must report performance at the same online planning-time budgets used in the benchmark. Improvements must not come from extra planning time, extra simulations after timeout, offline value precomputation over the benchmark seeds, or using information from future environment changes that is unavailable to the agent.

## Data and Generated Assets

The scientist may use only the benchmark environment definitions, generated roadmaps or geometry assets shipped with this workspace, and reproducible assets created by the benchmark scripts. External demonstrations, expert trajectories, learned policies trained on additional rollouts outside the benchmark protocol, or alternative terrain/map datasets are not allowed unless the benchmark is explicitly extended with a separate score track.

## Baselines

RefPol, RefSolver, and POMCP comparisons must be run under the same seeds, environment parameters, macro-action length limits, discount factor, and planning-time budgets as the submitted planner. A submission cannot claim improvement by weakening baselines, changing their action spaces unfairly, or giving the submitted planner more favorable simulation conditions.

## Macro Actions and Action Proposals

The benchmark should keep the paper's macro-action limits fixed: length 10 for the 3D maze and length 15 for HEMS. A scientist may improve how candidate actions are selected or evaluated, but must not bypass the online POMDP setting by executing a precomputed complete mission route that ignores observations and replanning.

## Randomness and Reporting

The scientist must evaluate on the fixed seed set and report all configured time budgets, not only the best-looking subset. Failed, timed-out, or collision episodes must remain in the aggregate metrics.

## Compliance Checklist

- [ ] Planner does not use privileged true state information for action selection beyond observations available to the agent.
- [ ] Maze environment, rewards, noise, start belief, goals, landmarks, danger zones, and termination rules are unchanged.
- [ ] HEMS terrain, objectives, no-fly-zone schedule, rewards, noise, and termination rules are unchanged.
- [ ] Planning-time budgets match the benchmark and no extra computation is used after timeout.
- [ ] No external demonstrations, expert policies, or additional training datasets are used.
- [ ] Baselines are evaluated with the same seeds and budgets as the submitted planner.
- [ ] Macro-action length limits remain 10 for maze and 15 for HEMS.
- [ ] All fixed evaluation seeds and all configured time budgets are reported.
