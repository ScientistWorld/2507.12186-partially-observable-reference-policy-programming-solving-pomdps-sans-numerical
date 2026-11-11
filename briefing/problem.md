# Problem Definition

This benchmark is about online planning for long-horizon partially observable Markov decision processes (POMDPs) with continuous states and actions. Before each executed action, an agent must choose a macro action from an uncertain belief, using a generative model of the task and a limited amount of computation. Observations are sparse.

## Research question

Can an online POMDP planner reliably solve a long-horizon navigation task under poor localisation? Before acting, it gets only a small, fixed planning budget per step. It is given a useful domain heuristic for proposing actions, but executing that heuristic directly is unreliable.

## The paper's tasks

The source paper evaluates two tasks:

- **3D maze with poor localisation.** A holonomic drone starts at one of two known positions with equal probability. It observes its position only when touching a landmark, and must reach a goal region while avoiding danger zones.
- **HEMS mission with evolving no-fly zones.** A helicopter in a Corsica terrain model must visit two victim locations while reacting to no-fly zones that appear at times unknown to it.

Neither simulator has been released.

## The task in this gym

The gym uses a scaled, procedurally generated version of the first task. Each instance is a closed 2D maze (44×30 cells) with interior walls.

**What the agent knows:**
- The robot starts at one of two known positions on the west side, with equal probability, and never learns which.
- The full map, the dynamics and the reward model.

**Actions and motion:**
- Each primitive step moves the robot one unit in any chosen heading.
- Gaussian noise with covariance 0.02·I is added to every step.
- Motion slides along walls and never passes through them.
- A decision is a macro action: an open-loop sequence of 1–10 headings.

**Observations:**
- When the robot is inside a landmark disc, it observes its exact position.
- Otherwise it observes nothing.

**Rewards and termination:**

| Event | Reward | Ends episode? |
|---|---:|---|
| Enter one of the two goal regions | +2000 | yes |
| Enter a danger zone | −500 | yes |
| Any other step | −5 | no |

- Discount factor 0.99.
- Horizon 200 primitive steps.
- Layouts are built so that a route planned for one start runs into a danger zone if executed from the other start. Acting on a wrong belief is costly.

**Domain knowledge available to agents:**
- A lattice roadmap of the free space.
- A heuristic action sampler that, for a given state, returns a truncated roadmap path to a random landmark or goal.
- A particle belief update.

All three live in `data/maze2d.py`. The heuristic alone is a weak policy.

## Why it matters

Autonomous systems often have to plan under uncertainty with limited computation. Observations are incomplete, and the cost of acting on a wrong belief is high. Better online POMDP planners make long-horizon decision making under such conditions safer and more reliable.

## Success criteria

A good planner:
- reaches a goal on a high fraction of unseen layouts;
- achieves high discounted return (reaching the goal sooner is better);
- rarely enters a danger zone;
- stays within the CPU planning budget;
- remains strong when the budget is tight.
