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
