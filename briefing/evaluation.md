# Evaluation

Evaluation measures online planner performance on the two benchmark POMDP scenarios described in the paper. This document specifies the task metrics and comparison protocol without assuming any particular solution method.

## Metrics

- **Expected total reward:** mean cumulative discounted reward over independent evaluation episodes. Higher is better. Report the mean and uncertainty estimate in the same form as the paper.
- **Success rate:** percentage of evaluation episodes in which the agent completes the mission objective before terminating unsuccessfully or exhausting the episode budget. Higher is better.
- **Planning-time response:** change in expected total reward and success rate as the allowed online planning time per decision increases. Better planners should show a non-negative trend across practical time budgets.
- **Baseline gap:** difference in reward and success rate relative to the reference-policy-only baseline, the reference-based online solver baseline, and the POMCP baseline under matched task and timing conditions.

## Baselines and Targets

The paper reports 100-run averages for each setting.

### 3D Maze with Poor Localisation

Maximum macro-action length is 10. The reported target system reaches:

- 1 second: 71% success, 570.3 +/- 183.5 expected total reward.
- 2 seconds: 75% success, 628.9 +/- 191.3 expected total reward.
- 3 seconds: 80% success, 625.0 +/- 215.2 expected total reward.
- 5 seconds: 81% success, 688.3 +/- 200.1 expected total reward.
- 10 seconds: 88% success, 873.4 +/- 172.1 expected total reward.
- 15 seconds: 94% success, 983.1 +/- 168.0 expected total reward.

The comparison baselines are RefPol, RefSolver, and POMCP. RefPol reports 29% success and -572.2 +/- 231.1 reward. At 10 seconds, RefSolver reports 30% success and -384.0 +/- 213.3 reward, while POMCP reports 13% success and -1897.5 +/- 240.1 reward.

### HEMS Mission with Evolving No-Fly Zones

Maximum macro-action length is 15. The reported target system reaches:

- 1 second: 58% success, 11393.5 +/- 1588.4 expected total reward.
- 2 seconds: 75% success, 15408.8 +/- 1399.3 expected total reward.
- 3 seconds: 78% success, 16207.7 +/- 1316.7 expected total reward.
- 5 seconds: 78% success, 16231.6 +/- 1320.2 expected total reward.
- 10 seconds: 90% success, 19393.5 +/- 967.9 expected total reward.

The comparison baselines are RefPol, RefSolver, and POMCP. RefPol reports 0% success and -6584.3 +/- 379.5 reward. At 10 seconds, RefSolver reports 22% success and 2258.7 +/- 2809.2 reward, while POMCP reports 0% success and -839.6 +/- 227.4 reward.

## Evaluation Protocol

Run each planner for 100 independent episodes per environment and time budget, using the same environment dynamics, reward rules, discount factor, macro-action length limit, and online planning-time limit used by the paper. Report results separately for each environment and time budget rather than pooling tasks.

Use fixed random seeds or a recorded seed list so that different planners face the same initial-state uncertainty, transition noise, observation noise, and environment-change schedule. The discount factor is 0.99 in both environments. For fair comparison, all planners must use the same generative model, reward function, termination rules, and macro-action execution semantics.

The 3D maze evaluation should include the poor-localisation initial belief, landmark-only localisation observations, danger-zone termination penalty, goal reward, and step penalty. The HEMS evaluation should include the Corsica terrain, two unordered objectives, evolving no-fly-zone penalties, collision termination penalty, mission-completion bonus, noisy transitions, noisy state readings, and step penalty.
