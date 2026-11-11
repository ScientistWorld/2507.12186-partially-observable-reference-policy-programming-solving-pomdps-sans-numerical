# Verification Report

## Final state

The final hardening iteration rebuilt the evaluation around evaluator-owned rollouts on hidden layouts with an enforced CPU budget. The evidence is in `HARDENING.md`, which reports:
- reference, baselines and variants on 300 hidden layouts;
- the seed spread;
- every shortcut from `REDTEAM.md` and the new ones, with before/after scores.

`python validate.py --compare` passes.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: medium-high for the scoring design; medium for fidelity to the paper's original (unreleased) simulators.
- Known limitations (see HARDENING.md, sections 4 and 7):
  - an agent could read `eval/test/` files while it runs;
  - a CPU budget rewards implementation speed;
  - the reference's time-based planning makes reruns differ by about one seed's spread.
