# Research Direction

## Research problem

Online planning for long-horizon POMDP navigation, with continuous states, macro actions, very sparse localisation, delayed rewards and a hard per-step computation budget.

## Core contribution sought

Better online belief-space planning: deciding, before each executed macro action, which candidate actions to explore and how to estimate their long-term value under an uncertain belief. The goal is to turn a useful but unreliable domain heuristic into a reliable policy, especially when computation is scarce.

## In scope

- Search and selection rules.
- Value backups and value estimates.
- Belief representation and update.
- Candidate-action generation.
- Allocation of the planning budget across decisions.
- Variance reduction.
- Learned components trained on self-generated layouts.
- More efficient implementations.

All of these must stay within the evaluator's CPU allowance on unseen layouts.

## Out of scope

- Reading hidden evaluation files, or otherwise obtaining the true start or noise.
- Exceeding or evading the compute allowance (other processes, reset-time planning).
- Changing the evaluator, the task constants or the scoring.
- Hard-coding behaviour for specific evaluation layouts.
