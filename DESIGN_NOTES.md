# Train/Test Evaluation Design Notes

- **Independent evaluators.** `eval/train/` and `eval/test/` are independent copies (no imports between them). Each has its own dynamics (`maze_env.py`, arithmetic identical to the public model `data/maze2d.py`) and its own instance list. Train has 100 public layouts with public generator seeds. Test has 300 layouts from random seeds that were never stored.
- **Instance fields only the evaluator uses.** `env_seed` (noise stream) and `true_start` (balanced). Agents receive only the public keys.
- **Discovery.** Both evaluators discover every manifest in `checkpoints/agents/`. The test also adds every method name reported in `scoring/scores_train.json`; a name without an agent gets worst values.
- **Budget.** CPU time of the agent's process tree, read from `/proc`, with orphans kept countable by a subreaper. Allowances are in units of a pure-Python stepping benchmark measured on the running machine: 8 / 1.6 units per declared primitive step, 0.05 s slack per episode, 100 units for reset, 4000 units for start-up.
- **Failures.** Crash, malformed or non-finite output, an oversized macro, a timeout, or a budget violation make the episode score worst (success 0, return −500, collision 1).
- **Scores files.** `scores_*.json` hold `results` (scored) and `_diagnostics` (not scored: failure reasons, budget use, wall time).
- After editing `eval/test/evaluate.py`, mirror the change into `eval/train/evaluate.py` by hand. The only differences are `SLICE`, the output path, and the train-name union that exists only in test.
