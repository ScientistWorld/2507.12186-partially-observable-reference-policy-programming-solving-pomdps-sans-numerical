# Scientist Constraints

## Environment

Use the provided scaled maze POMDP in `data/maze_pomdp.py` without changing the
reward values, start distribution, observation process, transition noise,
danger region, goal region, episode horizon, or macro-action definitions.
Changing the environment would make scores incomparable.

## Evaluation

Evaluate by writing JSONL episode artifacts with the same fields used by the
current method and baseline, then run `scripts/evaluate.sh`. Do not edit
`eval/` to favor a method.

## Resources

Use the same episode budget and random seed protocol as `scripts/reproduce.sh`
unless explicitly reporting an additional experiment. Improvements should come
from planning methodology, not from evaluating on easier seeds.

## Compliance Checklist

- [ ] `data/maze_pomdp.py` task dynamics and rewards are unchanged
- [ ] `scripts/evaluate.sh` is used to produce `scoring/scores.json`
- [ ] Episode artifacts include both success and total reward
- [ ] RefPol remains the heuristic-only baseline for comparison
