# Partially Observable Reference Policy Programming: Solving POMDPs Sans Numerical Optimisation

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2507.12186"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2507.12186-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2507.12186](https://arxiv.org/abs/2507.12186) |
|:---|:---|
| **Domain** | Online POMDP Planning / Robotics / Decision Making Under Uncertainty |
| **TL;DR** | The paper proposes an anytime online POMDP solver that uses KL-constrained policy improvement and deep sampled histories to outperform online planning baselines on long-horizon robotic navigation tasks. |

## Summary

The paper targets long-horizon POMDPs where continuous or large action spaces make exhaustive action enumeration expensive and myopic. It builds on reference-based POMDPs by turning the reference policy into a sequence of gradually updated policies rather than a fixed prior. The resulting PORPP planner combines particle beliefs, macro actions, heuristic action proposals, progressive widening, and preference-based backups. Experiments on a poorly localized 3D maze and an evolving Corsica helicopter rescue mission show much higher success rates and rewards than RefPol, RefSolver, and POMCP under matched online planning budgets.

## Problem

Can an online POMDP planner solve long-horizon robotic navigation tasks with large continuous action spaces, sparse delayed rewards, partial observability, and dynamically changing hazards, while using only a small amount of planning time before each executed action?

The paper evaluates this question on two tasks:

- **3D maze with poor localisation:** a holonomic drone starts from one of two possible locations, receives position observations only at landmarks, and must reach a goal while avoiding danger zones.
- **HEMS mission with evolving no-fly zones:** a holonomic helicopter in a Corsica terrain model must visit two unordered victim locations while reacting to no-fly zones that appear at unknown fixed time steps.

## The paper's method

The paper introduces **Partially Observable Reference Policy Programming (PORPP)**, an anytime online approximate POMDP solver. Its central idea is to repeatedly improve a stochastic policy through a sequence of reference-based POMDP objectives, where each new policy is constrained by a KL penalty to stay close to the previous policy.

This gives the planner a way to use informative action proposals for deep history sampling without permanently committing to a possibly misspecified reference policy.

## Key results of the paper

- On the 3D maze, the reported system reaches 94% success and 983.1 +/- 168.0 expected total reward with 15 seconds of planning per decision.
- On the HEMS mission, the reported system reaches 90% success and 19393.5 +/- 967.9 expected total reward with 10 seconds of planning per decision.
- The heuristic-only policy performs poorly in both domains, supporting the claim that successful performance requires online planning rather than only good action proposals.

## Leaderboard

FNI of AI scientists on this paper, grader-verified. 0 matches the paper's method, higher is better.

| Model | Innovate |
|---|---:|
| `gpt-5.6-terra-xhigh` | +106.2 |
| `gpt-5.5-xhigh` | +104.8 |
| `gpt-5.6-luna-xhigh` | +97.0 |
| `gpt-5.6-sol-xhigh` | +95.5 |

`innovate`: the model designs its own method. `improve`: it starts from the paper's method.

## Run it

```bash
pip install sciworld
sw research 2507.12186 --mode innovate --agent claude-code
sw evaluate 2507.12186
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

