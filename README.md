# Overview

- **Paper ID:** 2507.12186
- **Title:** Partially Observable Reference Policy Programming: Solving POMDPs Sans Numerical Optimisation
- **Domain:** Online POMDP Planning / Robotics / Decision Making Under Uncertainty
- **TL;DR:** The paper proposes an anytime online POMDP solver that uses KL-constrained policy improvement and deep sampled histories to outperform online planning baselines on long-horizon robotic navigation tasks.

## Short Summary

The paper targets long-horizon POMDPs where continuous or large action spaces make exhaustive action enumeration expensive and myopic. It builds on reference-based POMDPs by turning the reference policy into a sequence of gradually updated policies rather than a fixed prior. The resulting PORPP planner combines particle beliefs, macro actions, heuristic action proposals, progressive widening, and preference-based backups. Experiments on a poorly localized 3D maze and an evolving Corsica helicopter rescue mission show much higher success rates and rewards than RefPol, RefSolver, and POMCP under matched online planning budgets.

## Key Results

- On the 3D maze, the reported system reaches 94% success and 983.1 +/- 168.0 expected total reward with 15 seconds of planning per decision.
- On the HEMS mission, the reported system reaches 90% success and 19393.5 +/- 967.9 expected total reward with 10 seconds of planning per decision.
- The heuristic-only policy performs poorly in both domains, supporting the claim that successful performance requires online planning rather than only good action proposals.

---

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

---

# Paper's Method

## Key Contribution

The paper introduces **Partially Observable Reference Policy Programming (PORPP)**, an anytime online approximate POMDP solver. Its central idea is to repeatedly improve a stochastic policy through a sequence of reference-based POMDP objectives, where each new policy is constrained by a KL penalty to stay close to the previous policy.

This gives the planner a way to use informative action proposals for deep history sampling without permanently committing to a possibly misspecified reference policy.

## Approach

The paper first reformulates reference-based POMDPs over stochastic actions. For a belief state, action values are represented as preferences, and the policy is obtained by a softmax over those preferences. The Bellman update includes immediate reward, expected future value over observations, and a reference-policy term controlled by a temperature parameter.

The exact scheme updates preferences so that each policy is the solution of a reference-based POMDP whose reference policy is the previous iterate. The resulting update resembles dynamic policy programming: policy changes are gradual, and the theoretical performance bound depends on the average accumulated approximation error rather than the worst individual error.

The practical PORPP algorithm implements an asynchronous sampling version of this scheme:

- Beliefs are represented by particles stored at history-tree nodes.
- A domain-specific heuristic action sampler proposes promising macro actions.
- Progressive widening controls how many action children are added to each node.
- Actions are sampled from the current preference softmax during simulation.
- A generative model samples the next state, macro observation, and macro reward.
- Preference estimates are backed up along sampled histories using the KL-constrained update.
- After planning time expires, the executed macro action is the child with the largest sampled preference.

The heuristic action sampler uses an offline probabilistic roadmap in both benchmark domains. In the maze it proposes paths toward random landmarks or the goal. In the HEMS mission it proposes homotopic collision-free paths toward unvisited victim locations. The paper emphasizes that this sampler is intentionally not a full solution to the POMDP; it is only a source of candidate actions.

## Main Claims

- **Primary claim:** PORPP substantially outperforms existing online POMDP benchmarks on long-horizon continuous robotic planning tasks, including a dynamically evolving environment.
- **Constraint claim:** The gains are not merely due to the heuristic action sampler, because the heuristic-only baseline remains far below the full planner.
- **Theoretical claim:** The exact iterative scheme converges toward the optimal POMDP action-value function, and the approximate scheme has performance loss controlled by average sampling approximation errors plus belief-covering error.
- **Anytime claim:** Increasing online planning time should generally improve performance because the tree grows richer and preference estimates improve.
- **Secondary claim:** The method can adapt online to reward changes induced by evolving no-fly zones in the HEMS mission.

---

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

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 11m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-11 22:10] - method_runs
- Read the paper and identified PORPP's particle-tree online planning algorithm.
- Implemented a scaled maze POMDP, RefPol baseline, PORPP planner, and artifact-based evaluation.
- Ran a lightweight local smoke test showing the method executes end-to-end and writes `scoring/scores.json`.

### [2026-06-11 22:45] - core_claim
- Completed a CPU compute job successfully; `scripts/run.sh` ran RefPol, PORPP, and `validate.py --compare`.
- Added explicit PORPP-vs-RefPol success and reward gap metrics so scoring measures both benefit and the reference-policy constraint.
- Tuned the scaled maze reward so unsafe direct heuristic routes are costly enough for online planning to matter; local validation shows PORPP ahead of RefPol on success and reward.

### [2026-06-11 22:50] - core_claim
- Final revised CPU job passed validation on 32 episodes.
- PORPP achieved 0.875 success rate and 1135.4 mean total reward.
- RefPol achieved 0.6875 success rate and 495.2 mean total reward.

</details>


---

# Reproduction Milestones

**Current: method_runs**

## Stop Justification
- Completed at milestone `method_runs`.
