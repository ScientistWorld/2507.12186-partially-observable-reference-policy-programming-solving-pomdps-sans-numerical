# Paper's Method

## Key contribution

The paper introduces **Partially Observable Reference Policy Programming (PORPP)**, an anytime online approximate POMDP solver. It repeatedly improves a stochastic policy through a sequence of reference-based POMDP objectives. Each new policy is held close to the previous one by a KL penalty: a KL-constrained policy improvement, in the style of dynamic policy programming. As a result, informative action proposals can drive deep history sampling without the planner committing permanently to a possibly misspecified reference policy.

## Approach

**Preferences instead of values.** The paper first reformulates reference-based POMDPs over stochastic actions. Action values are represented as preferences Ψ(b, a), and the policy is the softmax exp(ηΨ) / Σ exp(ηΨ).

**Exact scheme.** Each policy solves a reference-based POMDP whose reference is the previous iterate:

Ψ_{k+1}(b, a) = Ψ_k(b, a) − [L_η Ψ_k](b) + R(b, a) + γ Σ_o P(o | a, b) [L_η Ψ_k](τ(b, a, o))

Here L_η is the log-sum-exp operator. The performance loss is bounded by the *average* of the accumulated approximation errors rather than the maximum (Theorems 1 and 2).

**Online algorithm (Algorithms 1–2), the asynchronous sampling version:**
- Beliefs are particle sets stored at history-tree nodes. Each visit adds the sampled state to the node's particles.
- Progressive widening: while |children(h)| < κ N(h)^α, the heuristic action sampler proposes one candidate macro action from the current particle. It is added if new.
- An action is sampled from the preference softmax. A state is resampled from b(h). The generative model returns the next state, the macro observation and the discounted macro reward.
- Backup: R(ha) and D(ha) are running means of the macro reward and the downstream value. Ψ(ha) ← Ψ(ha) − V(h) + R(ha) + γ^|a| D(ha), then V(h) ← (1/η) log Σ_a exp(η Ψ(ha)).
- Beyond the depth cut-off D_max, a value heuristic estimates the remaining value.
- When planning time is up, the child with the largest preference is executed. The root then moves to h a o, and particles consistent with the real observation are resampled into it.

**Heuristic action sampler.** In the paper it uses an offline probabilistic roadmap. It samples a random landmark or goal and returns the shortest roadmap path from the particle's position, truncated to the maximum macro length. It is deliberately not a solution to the POMDP.

## Implementation in this gym (`method/porpp.py`)

The algorithm follows Algorithms 1–2. Choices the paper leaves open:

| Setting | Value |
|---|---|
| η | 0.02 (1/η = 50 reward units) |
| Widening κ, α | 2, 0.5 |
| Depth cut-off D_max | 50 primitive steps |
| Root particles | 200 |
| Particles kept per tree node | 64 |
| Initial preference of a new child | the node's current value (or the value heuristic at a new node) |
| Value heuristic | optimistic discounted value of the roadmap distance to the nearest goal |
| Tree branching on observations | landmark observations rounded to the unit grid |

**Roadmap.** The roadmap is a lattice over free cells that keeps 0.7 units of clearance from danger zones (`data/maze2d.py`, `Roadmap`).

**Planning time.** Planning time per decision follows the evaluator's announced CPU allowance (`PlanningClock`, 75% of the allowance). `--fixed-simulations` instead runs 300 (standard) or 50 (tight) SIMULATE calls per decision.

**Baselines:**
- `baseline/refpol.py`: executes the sampler's macro for a sampled particle.
- `baseline/pomcp.py`: UCB tree search that enumerates 16 equally spaced directional macros of length 10, with the same planning allowance, particle filter and value heuristic.
- RefSolver is not implemented.

## Main claims

- **Primary:** PORPP substantially outperforms online POMDP benchmarks (RefPol, RefSolver, POMCP) on long-horizon continuous navigation tasks.
- **Constraint:** the gains do not come from the heuristic sampler alone; heuristic-only RefPol stays far below.
- **Theory:** the exact scheme converges, and the approximate scheme's loss is controlled by average sampling errors plus a belief-covering error.
- **Anytime:** more planning time generally improves results (in the paper's maze, 71% at 1 s to 94% at 15 s).
- **Adaptivity:** the planner adapts online to reward changes from evolving no-fly zones (HEMS; not reproduced here).
