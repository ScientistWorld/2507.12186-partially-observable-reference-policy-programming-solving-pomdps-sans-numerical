# Train/Test Evaluation Design Notes

## Checks Performed

- Read `eval/train/evaluate_maze.py`, `eval/test/evaluate_maze.py`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `scoring/reference.json` side by side.
- Confirmed the split evaluators score method-produced `checkpoints/*_episodes.jsonl` artifacts and do not import from `method/`.
- Confirmed `evaluate_train.sh` calls `eval.train` and writes `scoring/scores_train.json`; `evaluate_test.sh` calls `eval.test` and writes `scoring/scores_test.json`.
- Grepped for train/test cross-imports, hardcoded method defaults, test scripts writing train score files, paper-agreement metrics, and score stubs.
- Ran `bash -n` on both split evaluation scripts. No experiments or evaluators were run.

## Changes Made

- Replaced the reward-sorted even/odd partition with a deterministic seed-hash split shared by train and test. This removes the row-order/reward-order shortcut where an artifact writer could place strong rows in the visible slice.
- Added `valid_episode_rate` to both slice evaluators. It measures whether selected artifact rows contain the required episode fields with valid types.
- Added `unique_seed_rate` to both slice evaluators. It penalizes duplicated or replayed episode rows that would otherwise inflate success or reward on the visible slice.
- Updated `scoring/reference.json` so all metric entries include `higher_is_better`, `coefficient`, and `description`.
- Added the two new artifact-integrity metrics to the scaled-maze experiment reference rows with neutral expected values of `1.0` for the existing method and baselines.

## Fixed Patterns

- Fixed schema incompleteness: several metrics in `reference.json` lacked required descriptions.
- Strengthened shortcut resistance against artifact manipulation: the previous train/test split was based on sorted row position and total reward, which made visible-slice row placement easier to exploit.
- Strengthened shortcut resistance against duplicated rows: future methods now expose low unique-seed coverage in both train and test scores.

## Runtime Concerns For Next Iteration

- The seed-hash split can be mildly imbalanced when the episode count is very small. Runner iteration should inspect train/test episode counts after actual artifacts are generated.
- The evaluator validates artifact shape and seed uniqueness, but it still trusts the reported `success`, `total_reward`, and `trace` values rather than replaying the environment. A stronger future pass could add a lightweight trace replay check if the action names and observations are sufficient.
- The old full evaluator has unused low/high-budget arguments, but the current reproduction script does not produce those artifacts. I did not add budget-sensitivity train/test metrics because doing so would make the split depend on files that are not currently produced.
- The paper markdown path given in the prompt was absent; the same paper was available at `/home/user/paper/2507.12186.md` and was used only for context on metric choice.
