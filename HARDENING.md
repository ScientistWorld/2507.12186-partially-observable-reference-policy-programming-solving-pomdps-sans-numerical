# Hardening report

**Short answer: better results now score higher, and the major shortcuts score worst.**

The old test scored episode files that the method wrote itself, on one fixed open map. It could not tell one simulation from 2,800, and seven shortcuts beat the reference (`REDTEAM.md`).

The new test owns the environment. The evaluator runs every registered agent (`checkpoints/agents/<name>.json`) live on 300 hidden maze layouts (`eval/test/instances.json`). It executes the agent's macro actions in its own copy of the dynamics, with its own noise. It computes success, discounted return and danger collisions itself, and it enforces the planning budget. It reads nothing an agent writes.

Results:
- A variant that uses its CPU budget more efficiently (`porpp_depth30`) beats the reference by about five times the reference's seed spread.
- The baselines are well below the reference.
- Every shortcut that was tried scores the worst value of every metric.

All "after" numbers come from verification job `48547e3f-053`, which ran the final code on the 300 hidden instances. Evidence:
- `redteam/hardening/results/`: per-case scores, per-episode records, and `summary.json`.
- The cases are in `redteam/hardening/agents.py` and `manifests/`; the runner is `redteam/hardening/run_checks.sh`.
- `redteam/hardening/analyze.py` computes the ranks.
- `redteam/hardening/results_job1/` holds the intermediate job `b741c670-caf` (200 instances, fixed-count reference).

**Rank convention** (same as `REDTEAM.md`). For each case, sum over both experiments and all scored metrics:

> weight × |coefficient| × (improvement over the reference, in the `higher_is_better` direction) / (population standard deviation of that metric across all cases in the cohort)

The reference is `porpp` in `scoring/scores_test.json`, so its Δrank is 0. The "after" cohort has 23 cases; the "before" cohort is the redteam's 25 cases. Absolute Δrank units therefore differ between before and after. Compare signs, and compare each case with that cohort's seed spread.

## 1. What changed

| Area | Before | After |
|---|---|---|
| Who produces the scores | The method wrote `checkpoints/*_episodes.jsonl`, including `success` and `total_reward`; the evaluator aggregated them. | The evaluator runs the agent online in `eval/test/maze_env.py`, with its own noise stream. Agents only send macro actions over a JSON-lines protocol. |
| Test inputs | One fixed open 20×20 map, known to everyone. The test was a hash split of seeds the method chose. | 300 procedurally generated 44×30 closed mazes. Their seeds were never stored, so the layouts exist only in `eval/test/instances.json`. The visible split is 100 public layouts in `eval/train/`. |
| Comparisons | Gaps to editable baseline files; claim flags in [0, 1]. | No cross-method metrics. Each method is scored on its own success, return and collisions. Every method sees the same true start and noise on each instance, so comparisons are paired. |
| Planning budget | None (simulation count was self-reported). | CPU time of the agent's whole process tree, measured from `/proc` by the evaluator. Allowance: `units_per_step × machine_unit` seconds per declared primitive step, pooled per episode, plus 0.05 s slack. The machine unit is re-measured on the running machine. Start-up (≈ 4000 units) and per-instance reset (100 units) have their own caps. Exceeding any cap fails the episode. |
| Failures | Empty or invalid files scored return 0 and a perfect standard error; missing methods disappeared. | Any crash, timeout, malformed or non-finite action, oversized macro, or budget violation makes the episode a failure with the worst value of every metric (success 0, return −500, collision 1). A method with no or a broken manifest, or a name reported on train with no agent, gets worst values for all 300 episodes in both experiments. Three consecutive timeouts fail the rest of that run. |
| Scored experiments | `paper_3d_maze` (weight 0.62) and `paper_hems` (0.37) were never emitted; only the scaled maze (weight 0.01) was scored. | `maze_standard_budget` (0.6) and `maze_tight_budget` (0.4), both always emitted. The paper's tables are kept unchanged under `_paper_3d_maze`, `_paper_hems` and `_paper_tables_full` in `scoring/reference.json`. |
| Metrics | 10, four of them stuck at their bound (claim flags, validity, seed uniqueness). | `success_rate` (coefficient 1.0, primary), `mean_return` (0.5), `collision_rate` (0.25, lower is better). None is at a bound for any method. |
| Environment and method | Open map with one goal; macros steered with the true state at every step; danger −1800; 4 candidate actions; macro length 5. | Restored to the paper's 3D-maze settings wherever they are dimension-free (`data/maze2d.py`). Two equally likely starts. Landmarks reveal the true position. Danger −500, goal +2000, −5 per step, γ = 0.99, motion noise covariance 0.02·I. Two goal regions, walls the motion conforms to. Open-loop macros of up to 10 headings that trace a roadmap path from a sampled particle to a random landmark or goal (the paper's PRM sampler on a lattice roadmap). One candidate per widening step. 200-step horizon. |
| Reference planning time | 700 fixed simulations, a different count from the scripts. | PORPP plans "while time permitting" (Algorithm 1): it simulates until 75% of the announced CPU allowance is used (`data.agent_protocol.PlanningClock`). POMCP uses the same rule. |

`method/porpp.py` is still Algorithms 1–2 of the paper. It keeps the particle-belief history tree, progressive widening, softmax sampling over preferences, and the backup `Psi <- Psi - V + R + gamma^|a| D` followed by the log-sum-exp value. New children start at the node's current value. This is an implementation choice: the paper leaves the initial preference unspecified, and this choice keeps ‖Ψ₀‖ ≤ Q_max.

## 2. Do better results score higher? (variants, before → after)

Before (old gym, `REDTEAM.md`, 18 test episodes), Δrank against a seed spread of 0.002161:

| Variant | Before Δrank |
|---|---:|
| one simulation | −0.000001 |
| 4× simulations | +0.000175 / +0.002166 / +0.001206 |
| RefPol | −0.056 |
| stronger candidate search | +0.006049 |
| exhaustive search | +0.006054 |

The test could not tell one simulation from 700, and exhaustive search solved every episode.

After (300 hidden instances). The paired column is the per-instance success difference against the reference, ± its standard error.

| Variant (same CPU allowance unless stated) | Std success | Std return | Std collision | Tight success | Tight return | Tight collision | Paired Δ success std / tight | Δrank |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `porpp_depth30`: depth cut-off 30 instead of 50, so more simulations per CPU-second | **0.893** | 861.5 | 0.107 | **0.763** | 641.0 | 0.237 | +0.043±0.024 / +0.060±0.031 | **+0.267** |
| `porpp_plus`: stratified root sampling + depth 30 + faster generative model + 100 root particles | 0.883 | 822.3 | 0.117 | 0.757 | 595.3 | 0.243 | +0.033±0.024 / +0.053±0.033 | +0.196 |
| **Reference `porpp`** | 0.850 | 781.3 | 0.150 | 0.703 | 538.9 | 0.297 | 0 | 0 |
| `porpp_fixed_sims`: previous reference, 300 / 50 fixed simulations | 0.847 | 772.8 | 0.153 | 0.703 | 526.3 | 0.297 | −0.003 / +0.000 | −0.017 |
| `porpp_seed2` / `porpp_seed1` (reference, other seeds) | 0.853 / 0.827 | 787.9 / 756.2 | 0.143 / 0.173 | 0.687 / 0.707 | 511.6 / 547.3 | 0.313 / 0.293 | +0.003 / −0.017; −0.023 / +0.003 | −0.026 / −0.051 |
| `ucb_candidates`: UCB mean backups over the same candidates | 0.833 | 790.4 | 0.167 | 0.667 | 495.9 | 0.333 | −0.017 / −0.037 | −0.104 |
| `porpp_stratified` alone | 0.820 | 723.2 | 0.180 | 0.697 | 502.7 | 0.300 | −0.030 / −0.007 | −0.116 |
| `localise_then_goal`: hand-coded, no search | 0.557 | 329.5 | 0.443 | 0.577 | 358.6 | 0.423 | −0.293 / −0.127 | −1.101 |
| `bruteforce_sequences`: all target sequences to depth 3 (2 when tight) | 0.567 | 414.6 | 0.433 | 0.527 | 355.3 | 0.473 | −0.283 / −0.177 | −1.116 |
| `goal_direct` (constant goal) | 0.397 | 152.2 | 0.603 | 0.453 | 240.8 | 0.547 | −0.453 / −0.250 | −1.759 |
| `porpp_one_sim` (weaker) | 0.317 | −125.2 | 0.677 | 0.313 | −117.5 | 0.673 | −0.533 / −0.390 | −2.431 |
| `refpol` (paper baseline) | 0.233 | −215.8 | 0.747 | 0.270 | −194.6 | 0.713 | −0.617 / −0.433 | −2.740 |
| `pomcp` (paper baseline, 16 directional macros) | 0.010 | −426.9 | 0.000 | 0.027 | −414.2 | 0.043 | −0.840 / −0.677 | −3.117 |

**Reference seed noise** (three seeds): success spread 0.027 (standard) and 0.020 (tight); return spread 32 and 36; Δrank spread **0.051**.

**`porpp_depth30` beats the reference beyond noise.** Its Δrank of +0.267 is about five times the seed spread. It is ahead in all six metrics. The weighted paired success gain is 0.6·0.043 + 0.4·0.060 = 0.050 ± 0.019 (z ≈ 2.6). It is an honest change to an unspecified setting of the paper (the depth cut-off), measured at the same CPU allowance.

**The order of the rest is right.** The weaker variant, the baselines and the search-free policies all rank far below the reference. The paper's claim holds in the paper's direction, at both budgets: PORPP beats RefPol (+0.62 / +0.43 paired success) and POMCP (+0.84 / +0.68). POMCP's near-zero success matches the paper's account: a myopic, exhaustively enumerating search over directional macros stalls against walls. The paper itself reports 7–13% in its maze and 0–2% in HEMS.

**One trade-off.** Because the reference plans to a CPU deadline, its outcomes differ run to run by about a seed's worth (above). The fixed-count variant is exactly reproducible, but it leaves about 45% of the allowance unused.

## 3. Shortcuts: fix and score, before → after

All "after" rows ran through `eval/test/evaluate.py`, the code behind `scripts/evaluate_test.sh`. Shortcuts that fail every episode ran on the first 100 instances (40 for the two expensive ones). Every such shortcut scores success 0, return −500, collision 1 in both experiments: Δrank **−3.924**, the cohort minimum.

| Shortcut (before) | Before | Fix | After |
|---|---|---|---|
| `shortcut_fabricated_success` (invented success rows) | 1 / 2000, Δrank +0.006063 | The evaluator computes outcomes from its own rollouts; agent files are never read. | `shortcut_fabricate` writes fake episode and score files, then speaks no protocol: "expected hello" on 100/100 → worst. |
| `shortcut_baseline_sabotage` | +0.012547 | No cross-method metrics; baselines are only reported. | Baselines replaced by crashing agents: `porpp` still ran every episode without failure (0.80 / 0.69 on the first 100; 0.85 / 0.69 in the reference run, which is time-based run-to-run noise). Baselines get worst values. |
| `shortcut_select_success`, `shortcut_public_split_filter` (drop failed episodes) | +0.005957 each | The evaluator chooses the instances. Test layouts are hidden, and every instance is always scored. | Not expressible; missing episodes count as failures (`summarize`). |
| `shortcut_relabel_replay` (copy one good trajectory) | +0.006063 | Same as above, plus per-instance hidden noise. | Not expressible. |
| `shortcut_easier_environment` (edit the goal radius) | +0.006063 | The evaluator uses its own dynamics (`eval/test/maze_env.py`) and instance specs. | `shortcut_easier_model` plans with goals 8× larger: 0.163 / 0.103 success, Δrank −3.257. |
| `shortcut_fixed_map` (hard-coded route) | +0.006051 | Hidden procedurally generated layouts. | Not expressible. The closest search-free policies score −1.10 (`localise_then_goal`) and −1.76 (`goal_direct`). |
| `shortcut_missing_method` (empty train results) | tie (0) | Test discovers all manifests on disk, plus every name reported in `scores_train.json`. | A name with no agent gets worst values in all 300 × 2 episodes. |
| `shortcut_unlisted_method` | tie (0) | Same as above. | Every manifest is scored. All 23 cases in this report were discovered from a manifest directory. |
| `shortcut_failed_huge_reward`, `shortcut_invalid_numbers`, `shortcut_empty` | −0.047 / −0.088 / −0.088 (empty got return 0 and a perfect standard error) | Return is computed by the evaluator; it is in [−500, 2000) by construction. Failures get worst values. | Not expressible. `shortcut_nan_output` (NaN headings) and `shortcut_huge_macro` (1,000-step macro) are rejected on 100/100 → worst. `shortcut_crash` → worst. |
| `shortcut_score_prewrite` | −0.086 | `scoring/scores_test.json` is written once, after all episodes. | Unchanged (fails). |
| `bruteforce` (all 4⁴ macro sequences solved 18/18) | +0.006054 | Larger maze, continuous candidates, 200-step horizon, CPU cap. | `bruteforce_sequences`: 0.567 / 0.527, Δrank −1.116. |
| Private search: more simulations with its own simulator copy (new) | n/a | CPU allowance enforced on the process tree. | `porpp_private_search_3x` (3× the reference's CPU) would have reached 0.88 / 0.79 on its first 100 instances (reference: 0.85 / 0.69). The cap failed 98 / 91 of 100 episodes → Δrank −3.924. |
| Offloading search to a child process (new) | n/a | Process-tree accounting and subreaper. | `shortcut_offload_process` (4× CPU in a worker process): budget exceeded 40/40 → worst. |
| Planning during reset (new) | n/a | 100-unit per-instance reset cap. | `shortcut_reset_precompute` (20× a decision's simulations at reset): reset over budget 40/40 (39/40 tight) → worst. |
| Hanging agent (new) | n/a | Wall-clock safety timeouts; three consecutive timeouts fail the rest of the run. | Smoke-tested only (a 6-instance train run, not a job case): each experiment ended after 3 timeouts plus 3 skipped. |

## 4. Shortcuts left open, and why

- **An agent could read `eval/test/instances.json` while it runs.** The evaluator needs the hidden layouts, true starts and noise seeds on disk, and the agent runs as the same user. Reading them would reveal the true start and the noise, which would allow near-oracle play. This is a deliberate read of hidden test files that a separate grader can detect, so I did not build a sandbox (chroot or namespaces).
- **CPU budgets reward implementation speed.** As in the paper's wall-clock protocol, a faster implementation of the same algorithm gets more simulations. `porpp_plus` includes a 1.35×-faster generative model. A compiled implementation would gain more. This is an efficiency improvement at a matched budget, not a loophole, but it is not purely algorithmic.
- **The reference's 25% slack.** The reference plans to 75% of the allowance, so a planner that plans closer to the cap gets up to 1.33× more search. In `ucb_candidates`, planning to 75% still overshot once in 300 tight episodes; that episode scored as a failure.
- **Persistent processes.** One process serves consecutive episodes, so it can remember earlier hidden instances. Every instance is a new layout with its own noise, so memory can only carry general tuning across episodes. Background threads are counted, because CPU is measured over the whole process tree throughout each episode.
- **Machine calibration.** The machine unit is a pure-Python stepping benchmark. On a machine whose relative speed for tree-search code differs a lot from that benchmark, the allowance is only approximately matched. The reference's maximum episode use was 0.78 of the cap (standard) and 0.75 (tight).

## 5. Reference score before → after

| | Before (old test, 18 episodes) | After (300 hidden instances) |
|---|---|---|
| Scored success | 0.889 (`scaled_maze_online_planning`, weight 0.01) | **0.850 standard / 0.703 tight** |
| Return | 1160.0 | 781.3 / 538.9 |
| Collision rate | — | 0.150 / 0.297 |
| Claim flags | both 1.0 | — |
| Paper experiments | weights 0.62 and 0.37, never emitted | — |

The reference has no failed episodes. Its mean / maximum use of the allowance is 0.69 / 0.78 (standard) and 0.52 / 0.75 (tight).

On the visible split (100 instances) the reference scores 0.91 / 0.67 success, comparable to the test. RefPol scores 0.21 / 0.22 on train and 0.23 / 0.27 on test.

`scoring/scores_test.json`, `scores_train.json` and `scores.json` were regenerated from the reference runs alone (`porpp`, `refpol`, `pomcp`) with the final code, in job `48547e3f-053`.

## 6. Headroom check

**Bounds.** No scored metric sits at its bound for the reference: success 0.85 / 0.70 (bound 1), return 781 / 539, collision 0.15 / 0.30 (bound 0). The return bound depends on route length; in a light check on 40 visible layouts, a policy told its true start reached 100% success and a mean return of about 1180.

**Added experiment: `maze_tight_budget`.** This is the paper's own anytime study (Table 1, 1 s against 15 s): the regime where its method is weakest. The reference's success drops from 0.85 to 0.70.

**Variants above the reference:**
- `porpp_depth30` and `porpp_plus` (above) at the same allowance.
- Private search at 3× CPU would reach 0.88 / 0.79, which shows the task rewards better search, though the cap blocks it.

**Simple baselines and brute force stay far below:** RefPol 0.23, hand-coded localisation 0.56, exhaustive enumeration 0.57, at the standard budget.

**Weights.** The standard budget gets 0.6 because it carries the paper's central claim at practical planning times. The tight budget gets 0.4 because it adds headroom and tests the anytime claim. Within each experiment, success has coefficient 1.0 (the paper's headline metric), return 0.5 (reported alongside it, correlated, and also rewards shorter routes), and collision 0.25 (the danger-zone safety constraint, which the paper's maze is built around).

## 7. What I could not fix, plainly

- **The original simulators were never released.** The test is still a scaled stand-in: 2D instead of 3D, routes of 30–60 steps instead of about 100, a lattice roadmap instead of a random PRM. There is no HEMS / evolving no-fly-zone experiment, and no RefSolver baseline. The paper's numbers are kept as anchors, not targets.
- **The hidden test takes about 40 minutes on one CPU** for the three reference agents. POMCP accounts for about 30 minutes because it never terminates early.
- **Ranks are noisier than with fixed counts.** Time-based planning makes reruns of the reference differ by roughly the seed spread.
- **The old audit's executables no longer run.** `redteam/` outside `redteam/hardening/` targets the removed artifact-based gym (`data/maze_pomdp.py`, `eval/*/evaluate_maze.py`) and is kept only as the "before" record.
