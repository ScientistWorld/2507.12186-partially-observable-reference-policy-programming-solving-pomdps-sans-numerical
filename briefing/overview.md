# Overview

- **Paper ID:** 2507.12186
- **Title:** Partially Observable Reference Policy Programming: Solving POMDPs Sans Numerical Optimisation
- **Domain:** Online POMDP planning, robotics, decision making under uncertainty
- **TL;DR:** An anytime online POMDP solver that uses KL-constrained, gradual policy improvement over deeply sampled histories, and outperforms online planning baselines on long-horizon robotic navigation tasks.

## Short summary

The paper targets long-horizon POMDPs where large or continuous action spaces make exhaustive action enumeration expensive and myopic. It builds on reference-based POMDPs, but turns the reference policy into a sequence of gradually updated policies instead of a fixed prior. The resulting planner, PORPP, combines:
- particle beliefs,
- macro actions,
- heuristic action proposals,
- progressive widening,
- preference-based backups.

Experiments on a poorly localised 3D maze and an evolving Corsica helicopter rescue mission show much higher success rates and rewards than RefPol, RefSolver and POMCP under matched planning times.

## This gym

The original simulators were never released. The gym uses a scaled 2D version of the poor-localisation maze, with procedurally generated layouts (300 hidden test layouts, 100 public ones). The evaluator runs every agent online itself, enforces a CPU planning budget, and scores success, discounted return and danger collisions at two budget levels.

## Key results

| Source | Planner | Success |
|---|---|---|
| Paper, 3D maze | Proposed, 15 s | 94% |
| Paper, 3D maze | Proposed, 1 s | 71% |
| Paper, 3D maze | RefPol | 29% |
| Paper, 3D maze | POMCP, 10 s | 13% |
| Paper, HEMS | Proposed, 10 s | 90% |
| This gym, hidden test | PORPP, standard / tight budget | 85% / 70% |
| This gym, hidden test | RefPol | 23% / 27% |
| This gym, hidden test | POMCP | 1% / 3% |
