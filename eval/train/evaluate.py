"""Visible (train) evaluator for the partially observable maze benchmark.

The evaluator owns the environment.  For every agent registered under
``checkpoints/agents/<name>.json`` it starts the agent's command once per
episode, sends it the public description of a maze instance it has never seen,
executes the macro actions it returns in its own copy of the dynamics with its
own noise stream, and computes every scored number (success, discounted
return, danger collisions) itself.  Nothing an agent writes to disk is read.

The planning budget is enforced: the agent process tree's CPU time, measured
by the evaluator from /proc, may not exceed ``units_per_step * machine_unit``
seconds per primitive step of the macro actions it returned (the unit is
re-measured on the running machine); start-up (before the instance is sent)
and per-instance preparation (between reset and ready) have their own fixed
allowances.  A crash, malformed message, timeout or budget violation makes the
episode a failure with the worst value of every metric.

Every instance uses a fixed true start and a fixed per-step noise stream, so
all agents face identical randomness (paired comparisons).
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import random
import re
import select
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

from .maze_env import DANGER, GOAL, NONE, WORST_RETURN, TrueMaze

SLICE = "train"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INSTANCES = HERE / "instances.json"
DEFAULT_AGENTS_DIR = ROOT / "checkpoints" / "agents"
DEFAULT_OUT = ROOT / "scoring" / "scores_train.json"

# Budget levels.  units_per_step is CPU seconds per declared primitive step,
# in units of the machine calibration below (seconds per 1000 calibration
# steps).  Fixed by the evaluator; agents are told the resulting seconds.
EXPERIMENTS = {
    "maze_standard_budget": {"level": "standard", "units_per_step": 8.0},
    "maze_tight_budget": {"level": "tight", "units_per_step": 1.6},
}
STARTUP_UNITS = 4000.0       # CPU allowance for interpreter start-up and imports (before the instance is known)
RESET_UNITS = 100.0          # CPU allowance for per-instance preparation after the reset message
BUDGET_SLACK_SECONDS = 0.05  # one-off per-episode slack for clock-tick granularity
RESET_TIMEOUT = 60.0         # wall-clock safety nets against hung agents
ACT_TIMEOUT_MIN = 10.0
MAX_CONSECUTIVE_TIMEOUTS = 3  # then the remaining episodes of that run are failed without starting the agent
MAX_LINE_BYTES = 1 << 20
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]{0,79}$")
CLK = os.sysconf("SC_CLK_TCK")


# --------------------------------------------------------------- calibration
_CAL_SPEC = {
    "grid": ["#" * 20] + ["#" + "." * 18 + "#" for _ in range(12)] + ["#" * 20],
    "starts": [[2.0, 2.0], [2.0, 11.0]], "goals": [[18.5, 6.5, 0.4]], "dangers": [[10.0, 0.2, 0.5]],
    "landmarks": [[9.0, 7.0, 1.0]], "gamma": 0.99, "step_penalty": -5.0, "goal_reward": 2000.0,
    "danger_penalty": -500.0, "step_size": 1.0, "motion_noise_std": math.sqrt(0.02), "max_macro_len": 10,
    "horizon": 200,
}


def _calibration_once(steps: int = 20000) -> float:
    maze = TrueMaze(_CAL_SPEC)
    rng = random.Random(12345)
    t0 = time.process_time()
    x, y = 2.0, 2.0
    acc = 0.0
    for i in range(steps):
        heading = (i % 16) * 0.3926990816987241
        x, y, r, ev, _ = maze.step(x, y, heading, rng.gauss(0.0, maze.noise), rng.gauss(0.0, maze.noise))
        acc += r
        if ev != NONE:
            x, y = 2.0 + (i % 7), 2.0 + (i % 9)
    return (time.process_time() - t0) * 1000.0 / steps


def machine_unit() -> float:
    """CPU seconds per 1000 calibration steps on this machine (min of 5)."""
    return min(_calibration_once() for _ in range(5))


# ------------------------------------------------------------ process tree CPU
def _proc_cpu(pid: int) -> float:
    with open(f"/proc/{pid}/stat", "rb") as f:
        data = f.read()
    rest = data[data.rindex(b")") + 2:].split()
    return (int(rest[11]) + int(rest[12]) + int(rest[13]) + int(rest[14])) / CLK


def _children_from_task_files(pid: int) -> List[int]:
    out: List[int] = []
    try:
        for tid in os.listdir(f"/proc/{pid}/task"):
            try:
                with open(f"/proc/{pid}/task/{tid}/children") as f:
                    out.extend(int(c) for c in f.read().split())
            except OSError:
                pass
    except OSError:
        pass
    return out


def _children_from_scan(pid: int) -> List[int]:
    out: List[int] = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat", "rb") as f:
                data = f.read()
            if int(data[data.rindex(b")") + 2:].split()[1]) == pid:
                out.append(int(entry))
        except (OSError, ValueError, IndexError):
            continue
    return out


_HAS_CHILDREN_FILES = os.path.exists(f"/proc/self/task/{os.getpid()}/children")


def _children(pid: int) -> List[int]:
    if _HAS_CHILDREN_FILES:
        return _children_from_task_files(pid)
    return _children_from_scan(pid)


def descendants_cpu() -> float:
    """CPU seconds of every live descendant of this evaluator process
    (an agent's reaped children are included through its cutime/cstime)."""
    total = 0.0
    stack = _children(os.getpid())
    seen = set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        try:
            total += _proc_cpu(pid)
        except (OSError, ValueError, IndexError):
            continue
        stack.extend(_children(pid))
    return total


def _become_subreaper() -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(36, 1, 0, 0, 0)  # PR_SET_CHILD_SUBREAPER: orphans stay countable
    except Exception:
        pass


def _kill_descendants() -> None:
    for _ in range(3):
        stack = _children(os.getpid())
        if not stack:
            break
        seen = set()
        while stack:
            pid = stack.pop()
            if pid in seen:
                continue
            seen.add(pid)
            stack.extend(_children(pid))
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        time.sleep(0.01)
        _reap()


def _reap() -> None:
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


# ------------------------------------------------------------------ protocol
class AgentError(Exception):
    pass


class Channel:
    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self.fd = proc.stdout.fileno()
        self.buf = b""

    def send(self, obj) -> None:
        try:
            self.proc.stdin.write((json.dumps(obj) + "\n").encode())
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as exc:
            raise AgentError(f"agent closed its input: {exc}")

    def recv(self, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            while b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue  # tolerate stray prints; only JSON objects count
                if isinstance(msg, dict) and "type" in msg:
                    return msg
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AgentError("timeout")
            ready, _, _ = select.select([self.fd], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(self.fd, 65536)
            if not chunk:
                raise AgentError("agent exited")
            self.buf += chunk
            if len(self.buf) > MAX_LINE_BYTES:
                raise AgentError("oversized message")


def parse_headings(msg: dict, max_len: int) -> List[float]:
    if msg.get("type") != "action":
        raise AgentError("expected an action message")
    headings = msg.get("headings")
    if not isinstance(headings, list) or not 1 <= len(headings) <= max_len:
        raise AgentError("headings must be a list of 1..max_macro_len numbers")
    out = []
    for h in headings:
        if isinstance(h, bool) or not isinstance(h, (int, float)) or not math.isfinite(float(h)):
            raise AgentError("non-finite or non-numeric heading")
        out.append(float(h))
    return out


# ------------------------------------------------------------------ episodes
PUBLIC_KEYS = ("id", "grid", "starts", "goals", "dangers", "landmarks", "gamma", "step_penalty", "goal_reward",
               "danger_penalty", "step_size", "motion_noise_std", "max_macro_len", "horizon")


def agent_seed(instance_id: str, experiment: str) -> int:
    digest = hashlib.sha256(f"{SLICE}:{experiment}:{instance_id}".encode()).hexdigest()
    return int(digest[:8], 16)


def failed(reason: str, **extra) -> dict:
    record = {"success": False, "return": WORST_RETURN, "collision": True, "failed": True, "reason": reason}
    record.update(extra)
    return record


def run_episode(command: List[str], instance: dict, experiment: str, unit: float) -> dict:
    cfg = EXPERIMENTS[experiment]
    maze = TrueMaze(instance)
    per_step_cap = cfg["units_per_step"] * unit
    reset_cap = RESET_UNITS * unit
    startup_cap = STARTUP_UNITS * unit
    public = {k: instance[k] for k in PUBLIC_KEYS}
    budget = {"level": cfg["level"], "cpu_seconds_per_step": per_step_cap, "units_per_step": cfg["units_per_step"],
              "machine_unit_seconds": unit, "reset_cpu_seconds": reset_cap, "startup_cpu_seconds": startup_cap}
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONHASHSEED"] = "0"
    err = tempfile.TemporaryFile()
    try:
        proc = subprocess.Popen(command, cwd=str(ROOT), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                                env=env, start_new_session=True)
    except (OSError, ValueError) as exc:
        err.close()
        return failed(f"could not start agent: {exc}")
    chan = Channel(proc)
    rng = random.Random(int(instance["env_seed"]))
    x, y = maze.starts[int(instance["true_start"])]
    total, disc, t, decisions = 0.0, 1.0, 0, 0
    allowed = BUDGET_SLACK_SECONDS
    cpu_ready = cpu_start = 0.0
    outcome = NONE
    try:
        chan.send({"type": "hello"})
        msg = chan.recv(RESET_TIMEOUT)
        if msg.get("type") != "hello":
            raise AgentError("expected hello")
        cpu_start = descendants_cpu()
        if cpu_start > startup_cap:
            return failed("start-up over budget", cpu_startup=cpu_start, startup_cap=startup_cap)
        chan.send({"type": "reset", "instance": public, "seed": agent_seed(instance["id"], experiment), "budget": budget})
        msg = chan.recv(RESET_TIMEOUT)
        if msg.get("type") != "ready":
            raise AgentError("expected ready")
        cpu_ready = descendants_cpu()
        if cpu_ready - cpu_start > reset_cap:
            return failed("reset over budget", cpu_reset=cpu_ready - cpu_start, reset_cap=reset_cap)
        observations = None
        while t < maze.horizon:
            chan.send({"type": "act", "step": t, "observations": observations})
            msg = chan.recv(max(ACT_TIMEOUT_MIN, 50.0 * per_step_cap * maze.max_macro_len))
            headings = parse_headings(msg, maze.max_macro_len)
            decisions += 1
            allowed += per_step_cap * len(headings)
            observations = []
            for heading in headings:
                ex = rng.gauss(0.0, maze.noise)
                ey = rng.gauss(0.0, maze.noise)
                x, y, reward, outcome, obs = maze.step(x, y, heading, ex, ey)
                total += disc * reward
                disc *= maze.gamma
                t += 1
                observations.append(list(obs) if obs is not None else None)
                if outcome != NONE or t >= maze.horizon:
                    break
            if outcome != NONE:
                break
        cpu_used = descendants_cpu() - cpu_ready
        try:
            chan.send({"type": "end"})
        except AgentError:
            pass
    except AgentError as exc:
        tail = b""
        try:
            err.seek(0)
            tail = err.read()[-400:]
        except OSError:
            pass
        return failed(str(exc), stderr_tail=tail.decode("utf-8", "replace"), decisions=decisions, steps=t)
    finally:
        _kill_descendants()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        for stream in (proc.stdin, proc.stdout):
            try:
                stream.close()
            except Exception:
                pass
        err.close()
    if cpu_used > allowed:
        # The would-be outcome is kept for diagnostics only; the episode scores as failed.
        return failed("planning budget exceeded", cpu_used=cpu_used, cpu_allowed=allowed, decisions=decisions, steps=t,
                      unscored_success=outcome == GOAL, unscored_return=total, unscored_collision=outcome == DANGER)
    return {
        "success": outcome == GOAL,
        "return": total,
        "collision": outcome == DANGER,
        "failed": False,
        "steps": t,
        "decisions": decisions,
        "cpu_used": cpu_used,
        "cpu_allowed": allowed,
        "cpu_reset": cpu_ready - cpu_start,
        "cpu_startup": cpu_start,
    }


# ------------------------------------------------------------------- scoring
def summarize(records: List[dict], expected: int) -> dict:
    # Missing episodes (never produced) count as failures too.
    recs = list(records) + [failed("missing")] * max(0, expected - len(records))
    n = len(recs)
    if n == 0:
        return {"success_rate": 0.0, "mean_return": WORST_RETURN, "collision_rate": 1.0}
    ok = [r["success"] for r in recs]
    return {
        "success_rate": sum(ok) / n,
        "mean_return": sum(r["return"] for r in recs) / n,
        "collision_rate": sum(1 for r in recs if r["collision"]) / n,
    }


def diagnostics(records: List[dict]) -> dict:
    n = max(1, len(records))
    reasons: Dict[str, int] = {}
    for r in records:
        if r.get("failed"):
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    fractions = [r["cpu_used"] / r["cpu_allowed"] for r in records if not r.get("failed") and r.get("cpu_allowed")]
    return {
        "episodes": len(records),
        "failed_episodes": sum(1 for r in records if r.get("failed")),
        "failure_reasons": reasons,
        "mean_steps": sum(r.get("steps", 0) for r in records) / n,
        "mean_decisions": sum(r.get("decisions", 0) for r in records) / n,
        "mean_budget_fraction": (sum(fractions) / len(fractions)) if fractions else None,
        "max_budget_fraction": max(fractions) if fractions else None,
    }


def load_manifest(path: Path) -> Optional[List[str]]:
    try:
        manifest = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    command = manifest.get("command") if isinstance(manifest, dict) else None
    if not isinstance(command, list) or not command or not all(isinstance(c, str) for c in command):
        return None
    if command[0] in ("python", "python3"):
        command = [sys.executable] + command[1:]
    return command


def method_key(stem: str) -> str:
    key = stem if NAME_RE.match(stem) else "agent_" + re.sub(r"[^A-Za-z0-9_.+-]", "_", stem).lstrip("_")
    return key[:80]


def discover(agents_dir: Path) -> Dict[str, Optional[List[str]]]:
    found: Dict[str, Optional[List[str]]] = {}
    if agents_dir.is_dir():
        for path in sorted(agents_dir.glob("*.json")):
            if path.name.startswith("."):
                continue
            found[method_key(path.stem)] = load_manifest(path)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents-dir", type=Path, default=DEFAULT_AGENTS_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--episodes-out", type=Path, default=None, help="optional per-episode records (JSON)")
    parser.add_argument("--only", nargs="*", default=None, help="restrict to these method keys")
    parser.add_argument("--limit", type=int, default=0, help="smoke test: first N instances only (not for scoring)")
    args = parser.parse_args()

    _become_subreaper()
    instances = json.loads(INSTANCES.read_text())
    if args.limit:
        instances = instances[: args.limit]
    methods = discover(args.agents_dir)
    if args.only is not None:
        methods = {k: v for k, v in methods.items() if k in set(args.only)}

    scores: Dict[str, dict] = {exp: {"results": {}, "_diagnostics": {}} for exp in EXPERIMENTS}
    episodes: Dict[str, dict] = {}
    for name, command in sorted(methods.items()):
        for exp in EXPERIMENTS:
            unit = machine_unit()
            records = []
            started = time.time()
            timeouts = 0
            for inst in instances:
                if command is None:
                    rec = failed("missing or invalid manifest")
                elif timeouts >= MAX_CONSECUTIVE_TIMEOUTS:
                    rec = failed("skipped after repeated timeouts")
                else:
                    rec = run_episode(command, inst, exp, unit)
                    timeouts = timeouts + 1 if rec.get("reason") == "timeout" else 0
                rec["instance"] = inst["id"]
                records.append(rec)
            scores[exp]["results"][name] = summarize(records, len(instances))
            diag = diagnostics(records)
            diag["machine_unit_seconds"] = unit
            diag["wall_seconds"] = round(time.time() - started, 1)
            scores[exp]["_diagnostics"][name] = diag
            episodes.setdefault(exp, {})[name] = records
            print(json.dumps({"slice": SLICE, "experiment": exp, "method": name, **scores[exp]["results"][name],
                              "failed": diag["failed_episodes"], "budget_fraction": diag["mean_budget_fraction"],
                              "wall_s": diag["wall_seconds"]}), flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2) + "\n")
    if args.episodes_out:
        args.episodes_out.parent.mkdir(parents=True, exist_ok=True)
        args.episodes_out.write_text(json.dumps(episodes) + "\n")


if __name__ == "__main__":
    main()
