# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-11 22:03] - core_claim
- Implemented the paper's PORPP asynchronous online preference-update algorithm on an accessible scaled maze POMDP preserving poor localization, macro actions, landmark observations, delayed goal reward, and unsafe direct routes.
- Ran PORPP and the RefPol heuristic-only baseline through the artifact evaluator; PORPP achieved 0.875 success and 1135.4 mean discounted reward versus RefPol's 0.6875 success and 495.2 mean discounted reward on 32 episodes.
- Added a POMCP-style particle tree-search baseline for the same scaled maze and submitted a follow-up job to score it alongside PORPP and RefPol.

## Stop Justification
- Current packaged milestone is `core_claim`; higher milestones would require additional original-paper environments or validated extensions beyond the accessible scaled maze.
