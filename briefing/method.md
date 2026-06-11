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
