"""Minimal helper for the evaluator's JSON-lines agent protocol.

An agent is any executable listed in ``checkpoints/agents/<name>.json``.  The
evaluator starts it once per episode and talks to it over stdin/stdout, one
JSON object per line (stdout is reserved for protocol messages; log to stderr):

  evaluator -> agent  {"type": "hello"}            (before the instance is known)
  agent -> evaluator  {"type": "hello"}
  evaluator -> agent  {"type": "reset", "instance": {...}, "seed": int,
                       "budget": {"level": str, "cpu_seconds_per_step": float, ...}}
  agent -> evaluator  {"type": "ready"}
  evaluator -> agent  {"type": "act", "step": int, "observations": null | [obs, ...]}
  agent -> evaluator  {"type": "action", "headings": [float, ...]}   (1..max_macro_len)
  evaluator -> agent  {"type": "end"}

``observations`` holds one entry per primitive step of the previous macro
action: ``null`` or the observed ``[x, y]``.  It is ``null`` on the first act.

``run_agent(factory)`` implements this loop for a policy object created by
``factory(instance, seed, budget)`` that exposes ``act(observations)``.
"""

from __future__ import annotations

import json
import sys
from typing import Callable


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
            break
