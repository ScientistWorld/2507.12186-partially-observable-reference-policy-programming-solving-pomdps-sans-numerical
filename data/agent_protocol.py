"""Minimal helper for the evaluator's JSON-lines agent protocol.

An agent is any executable listed in ``checkpoints/agents/<name>.json``.  The
evaluator starts it and talks to it over stdin/stdout, one JSON object per line
(stdout is reserved for protocol messages; log to stderr).  One process serves
consecutive episodes (reset ... end, reset ... end, ...) until ``shutdown`` or
end of input; a process that exits after ``end`` is simply restarted.

  evaluator -> agent  {"type": "hello"}            (before the instance is known)
  agent -> evaluator  {"type": "hello"}
  evaluator -> agent  {"type": "reset", "instance": {...}, "seed": int,
                       "budget": {"level": str, "cpu_seconds_per_step": float, ...}}
  agent -> evaluator  {"type": "ready"}
  evaluator -> agent  {"type": "act", "step": int, "observations": null | [obs, ...]}
  agent -> evaluator  {"type": "action", "headings": [float, ...]}   (1..max_macro_len)
  evaluator -> agent  {"type": "end"}                (next: reset again, or shutdown)

``observations`` holds one entry per primitive step of the previous macro
action: ``null`` or the observed ``[x, y]``.  It is ``null`` on the first act.

``run_agent(factory)`` implements this loop for a policy object created by
``factory(instance, seed, budget)`` that exposes ``act(observations)``.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Callable


class PlanningClock:
    """Tracks the evaluator's CPU planning allowance within one episode.

    The evaluator allows ``budget["cpu_seconds_per_step"]`` CPU seconds per
    primitive step of every macro action returned, pooled over the episode
    (plus a small fixed slack), measured on the whole agent process tree from
    the moment ``ready`` is sent.  ``deadline()`` returns the process CPU time
    (``time.process_time()``) at which the current decision should stop
    planning so that the episode stays at ``fraction`` of its allowance,
    assuming the next macro has ``assumed_length`` steps; call ``commit(len)``
    after each decision.  Create it at the end of reset handling.
    """

    def __init__(self, budget: dict, fraction: float = 0.75, assumed_length: int = 5):
        self.per_step = float(budget.get("cpu_seconds_per_step") or 0.0)
        self.fraction = fraction
        self.assumed_length = assumed_length
        self.steps = 0
        self.start = time.process_time()

    @property
    def active(self) -> bool:
        return self.per_step > 0.0

    def deadline(self) -> float:
        return self.start + self.fraction * self.per_step * (self.steps + self.assumed_length)

    def commit(self, macro_length: int) -> None:
        self.steps += int(macro_length)


def run_agent(factory: Callable) -> None:
    policy = None
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        kind = msg.get("type")
        if kind == "hello":
            out.write('{"type": "hello"}\n')
            out.flush()
        elif kind == "reset":
            policy = factory(msg["instance"], int(msg.get("seed", 0)), msg.get("budget", {}))
            out.write('{"type": "ready"}\n')
            out.flush()
        elif kind == "act":
            obs = msg.get("observations")
            if obs is not None:
                obs = [tuple(o) if o is not None else None for o in obs]
            headings = policy.act(obs)
            out.write(json.dumps({"type": "action", "headings": [float(h) for h in headings]}) + "\n")
            out.flush()
        elif kind == "end":
            policy = None
        elif kind == "shutdown":
            break
