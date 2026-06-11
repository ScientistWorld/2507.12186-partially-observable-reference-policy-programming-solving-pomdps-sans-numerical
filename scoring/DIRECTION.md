# Research Direction

## Research Problem

This paper addresses online planning for long-horizon POMDPs with large or continuous action spaces, sparse delayed rewards, partial observability, and changing environment costs. The scientific question is how to plan deeply enough to capture delayed outcomes without exhaustively enumerating an impractically large action space at every belief.

## Core Contribution

The paper's contribution is a reference-policy-programming approach for POMDPs: a planner improves a stochastic policy through gradual, KL-constrained updates while using sampled future histories for online decision making. Future work in this benchmark should improve this same family of reference-guided online POMDP planning methods, especially the way candidate actions, belief histories, and preference/value estimates are updated under limited planning time.

## Approach Scope

Scientists should work within online sampling-based POMDP planning for the same robotic navigation tasks. In-bounds changes include improving belief particle management, action proposal strategies, progressive widening rules, rollout/value heuristics, preference estimation, backup equations within the same reference-guided planning family, temperature or exploration schedules, and computational efficiency of the online tree search.

The method may use better domain heuristics or learned proposal components if they operate within the online POMDP protocol and do not replace planning with a precomputed policy. The submitted planner should still make decisions from beliefs and observations during execution.

## Out of Bounds

- Replacing the problem with fully observable planning, deterministic shortest-path search, or model-predictive control with privileged state.
- Training a generic end-to-end policy to imitate or solve the tasks without implementing a recognizable online POMDP planning procedure.
- Switching to an offline reinforcement-learning setup where the final policy acts without online planning.
- Using a complete precomputed route or schedule that encodes the benchmark solution instead of replanning from observations.
- Changing the benchmark environments, rewards, noise models, no-fly-zone schedule, or evaluation budgets to make the task easier.
- Claiming improvement from more compute, longer planning time, or additional external data rather than from a methodological change in online POMDP planning.
