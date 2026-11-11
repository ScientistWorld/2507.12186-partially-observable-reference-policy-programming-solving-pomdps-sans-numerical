# Experiment Overview

Both experiments use the same task and the same 300 hidden maze layouts; train uses 100 public layouts. The evaluator runs each agent itself and computes every number from its own rollouts. Every agent faces the same hidden start and noise on each layout.

## maze_standard_budget (weight 0.6)

**Question.** With a practical per-step planning budget, can an online planner turn an imperfect domain heuristic into a reliable policy for a long-horizon navigation task with very poor localisation?

**Setting.**
- The robot does not know which of two starts it is at.
- It observes its position only at landmarks.
- Acting on the wrong hypothesis can lead it into a danger zone.

**Scoring.** Success rate is the headline. Discounted return also rewards shorter routes. Collision rate is the safety side.

**Expected order.** The paper's reference planner should clearly beat:
- executing the heuristic directly;
- an exhaustively enumerating tree search over fixed directional moves;
- hand-coded or exhaustive-enumeration policies.

## maze_tight_budget (weight 0.4)

**Question.** The same question with about a fifth of the planning computation per step. This is the anytime regime: the paper's own study shows its planner is weakest here (71% success at its shortest time against 94% at its longest).

**What it shows.**
- How much performance a method keeps when computation is scarce.
- Where better use of a fixed budget pays off most.
