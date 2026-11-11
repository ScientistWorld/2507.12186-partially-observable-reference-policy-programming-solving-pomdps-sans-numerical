# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-11-11 00:30] - core_claim (hardening, final iteration)
- Replaced the artifact-reading evaluator with evaluator-owned online rollouts.
  Agents speak a JSON-lines protocol; the evaluator owns the dynamics and noise
  and runs on 300 hidden procedurally generated mazes, with an enforced and
  calibrated CPU planning budget. Failures score worst.
- Restored the paper's 3D-maze settings where dimension-free: two goals,
  -500 danger, true-position landmark observations, open-loop roadmap-path
  macros of length 10, noise covariance 0.02I.
- PORPP plans "while time permitting" against the CPU allowance.
- Scored experiments: `maze_standard_budget` (0.6), `maze_tight_budget` (0.4).
- Reference on the hidden test: success 0.850 / 0.703, against RefPol
  0.233 / 0.270 and POMCP 0.010 / 0.027.
- All tested shortcuts score worst; a better-search variant beats the
  reference beyond seed noise. See HARDENING.md.

### [2026-06-11 22:51] - core_claim
- Completed final verification after the optional mirrored-setting setup.
- Removed the unverified mirrored setting from official scoring targets and
  from the default reproduction script because no completed scored job existed
  for it.
- Kept the milestone at `core_claim`; the validated gym benchmark is the
  completed scaled-maze online-planning experiment.

### [2026-06-11 22:46] - core_claim
- Added a mirrored-danger scaled maze setting to test the core PORPP claim on
  a second layout without changing the algorithm or evaluation procedure.
- Updated method, RefPol, POMCP, and the artifact evaluator to carry a
  `scenario` field and score separate experiments from recursively discovered
  episode files.
- Prepared a CPU job to regenerate default and mirrored setting artifacts; the
  milestone remains `core_claim` until those results complete.

### [2026-06-11 22:41] - core_claim
- Completed final verification of folder structure, scoring, method/eval
  separation, train/test wiring, and method-agnostic documentation.
- Fixed the default evaluator so future candidate artifacts are discovered and
  scored automatically from `checkpoints/*_episodes.jsonl`.
- Wrote `VERIFICATION.md`; final judgment is ready for gym use at
  `core_claim`, with the documented limitation that the original simulators
  were unavailable and a scaled maze substitute is used.

### [2026-06-11 22:36] - core_claim
- Fixed the job entrypoint so `scripts/run.sh` regenerates all official
  episode artifacts through `scripts/reproduce.sh` before scoring full,
  visible-train, and held-out-test views.
- Added default evaluator checks for valid episode format and unique seeds,
  bringing `scoring/scores.json` in line with the reference scoring contract.
- Removed generated job logs from the git index and prepared a CPU validation
  submission for the revised end-to-end job path.

### [2026-06-11 22:12] - core_claim
- Reviewed the corrected CPU job `2c2a8d2f-ba9`. It exited successfully, wrote
  `scoring/scores.json`, and passed `python validate.py --compare`.
- Final scaled-maze scores: PORPP reached 0.875 success and 1135.4 mean reward,
  RefPol reached 0.6875 success and 495.2 mean reward, and corrected
  directional POMCP reached 0.28125 success and 239.7 mean reward.
- Fixed the scoring contract so the substitute environment's primary metric is
  the artifact-computed core-claim relation rather than a false direct
  comparison to original-simulator baseline success rates.
- The workspace is packaged as a reusable `core_claim` reproduction.

### [2026-06-11 22:25] - core_claim
- Audited the existing reproduction after milestone reset. The PORPP implementation is an actual particle-history-tree implementation of the paper's asynchronous preference programming algorithm, not a surrogate.
- Fixed scoring hygiene by replacing circular scaled-maze reference rows with paper Table 1-derived scale anchors while keeping the scaled experiment documented as a substitute because the original simulator is unavailable.
- Prepared a CPU job to regenerate `scores.json` with RefPol, POMCP, and PORPP artifacts.

### [2026-06-11 22:45] - core_claim
- Reviewed the completed CPU job. It validated successfully, but POMCP reached 100% success because it had been given the same target macro actions used by the domain heuristic.
- Corrected POMCP to enumerate fixed directional macro actions, matching the paper's POMCP baseline protocol more closely.
- Prepared a follow-up CPU job to regenerate scores with the corrected POMCP baseline.

### [2026-06-11 22:03] - core_claim
- Implemented the paper's PORPP asynchronous online preference-update algorithm on an accessible scaled maze POMDP preserving poor localization, macro actions, landmark observations, delayed goal reward, and unsafe direct routes.
- Ran PORPP and the RefPol heuristic-only baseline through the artifact evaluator; PORPP achieved 0.875 success and 1135.4 mean discounted reward versus RefPol's 0.6875 success and 495.2 mean discounted reward on 32 episodes.
- Added a POMCP-style particle tree-search baseline for the same scaled maze and submitted a follow-up job to score it alongside PORPP and RefPol.

## Stop Justification
- Completed at milestone `core_claim`.
