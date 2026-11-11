"""Variants and shortcut agents used to check the hardened evaluator.

Every entry is a normal agent (JSON-lines protocol) selected with --kind and
registered by a manifest in redteam/hardening/manifests/.  Honest variants use
only data/ and method/ (what a scientist sees); shortcuts try to obtain a
better score without a better planner.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

from data.agent_protocol import PlanningClock, run_agent
from data.maze2d import NONE, Maze, Roadmap, update_particles
from method.porpp import BUDGET_SIMULATIONS, ActionStats, Node, PORPPPlanner, obs_key

ROOT = Path(__file__).resolve().parents[2]


def level_sims(budget, scale=1.0):
    return max(1, int(round(BUDGET_SIMULATIONS.get(budget.get("level", "standard"), 300) * scale)))


# ------------------------------------------------------------ honest variants
class FastModel:
    """Same generative model as data.maze2d.Maze.macro, written for speed:
    cached heading velocities, inlined collision/event tests and a pool of
    pre-drawn Gaussian noise read from a random offset."""

    def __init__(self, maze: Maze):
        self._maze = maze
        self._vel = {}
        pool_rng = random.Random(12345)
        self._pool = [pool_rng.gauss(0.0, maze.noise) for _ in range(1 << 16)]

    def __getattr__(self, name):
        return getattr(self._maze, name)

    def macro(self, x, y, headings, rng):
        vel = self._vel.get(headings)
        if vel is None:
            v = self._maze.step_size
            vel = self._vel[headings] = [(v * math.cos(h), v * math.sin(h)) for h in headings]
        m = self._maze
        W, H, blocked = m.width, m.height, m.blocked
        dangers, goals, lands = m._danger_r2, m._goal_r2, m._land_r2
        gamma, sp = m.gamma, m.step_penalty
        pool = self._pool
        k = rng.getrandbits(16)
        disc, total, last, n = 1.0, 0.0, None, 0
        for vx, vy in vel:
            n += 1
            dx = vx + pool[k]
            dy = vy + pool[(k + 1) & 0xFFFF]
            k = (k + 2) & 0xFFFF
            nx, ny = x + dx, y + dy
            mx, my = x + 0.5 * dx, y + 0.5 * dy
            if (0.0 <= nx < W and 0.0 <= ny < H and not blocked[int(ny) * W + int(nx)]
                    and 0.0 <= mx < W and 0.0 <= my < H and not blocked[int(my) * W + int(mx)]):
                x, y = nx, ny
            elif (0.0 <= nx < W and not blocked[int(y) * W + int(nx)]
                  and 0.0 <= mx < W and not blocked[int(y) * W + int(mx)]):
                x = nx
            elif (0.0 <= ny < H and not blocked[int(ny) * W + int(x)]
                  and 0.0 <= my < H and not blocked[int(my) * W + int(x)]):
                y = ny
            for cx, cy, r2 in dangers:
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                    return x, y, total + disc * m.danger_penalty, 1, last, n
            for cx, cy, r2 in goals:
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                    return x, y, total + disc * m.goal_reward, 2, last, n
            total += disc * sp
            disc *= gamma
            for cx, cy, r2 in lands:
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                    last = (x, y)
                    break
        return x, y, total, NONE, last, n


def split_clusters(parts):
    """Two groups of root particles along the axis of largest spread, split
    at the largest gap (median when the belief is unimodal)."""
    xs = [p[0] for p in parts]
    ys = [p[1] for p in parts]
    ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
    srt = sorted(parts, key=lambda p: p[ax])
    if len(srt) < 2:
        return [srt, srt]
    gap, i = max((srt[j + 1][ax] - srt[j][ax], j) for j in range(len(srt) - 1))
    if gap < 1.0:
        i = len(srt) // 2 - 1
    a, b = srt[: i + 1], srt[i + 1:]
    return [a or b, b or a]


class StratifiedPORPPPlanner(PORPPPlanner):
    """PORPP with stratified root sampling: the state for the k-th simulation
    of a root action comes alternately from the two clusters of the root
    belief, so every candidate is evaluated under both start hypotheses.
    Preference backups are unchanged."""

    def plan(self, deadline=None):
        self._clusters = split_clusters(self.root.particles)
        return super().plan(deadline)

    def simulate(self, node, x, y, depth):
        if depth != 0:
            return super().simulate(node, x, y, depth)
        rng = self.rng
        node.visits += 1
        if len(node.actions) < self.kappa * node.visits ** self.alpha:
            key, target = self.roadmap.sample_key(x, y, rng)
            if key not in node.actions:
                headings = self.roadmap.path_headings(x, y, target, self.maze.max_macro_len)
                if node.actions:
                    init = node.value
                else:
                    init = self.roadmap.value_estimate(x, y)
                    node.value = init
                node.actions[key] = ActionStats(headings, init, self.maze.gamma)
        key, stats = self._sample_softmax(node)
        cluster = self._clusters[stats.visits % 2]
        sx, sy = cluster[rng.randrange(len(cluster))]
        nx, ny, reward, event, last_obs, steps = self.maze.macro(sx, sy, stats.headings, rng)
        stats.visits += 1
        n = stats.visits
        stats.reward_mean += (reward - stats.reward_mean) / n
        if event == NONE:
            ckey = (key, obs_key(last_obs))
            child = node.children.get(ckey)
            if child is None:
                child = Node([(nx, ny)])
                node.children[ckey] = child
            downstream = self.simulate(child, nx, ny, depth + steps)
        else:
            downstream = 0.0
        stats.downstream_mean += (downstream - stats.downstream_mean) / n
        stats.preference = stats.preference - node.value + stats.reward_mean + stats.discount * stats.downstream_mean
        node.value = self._log_sum_exp(node)
        return node.value


class PlannerAgent:
    """PORPP-family agent.  By default it plans against the evaluator's CPU
    allowance exactly like the reference (PlanningClock, fraction 0.75)."""

    def __init__(self, instance, seed, budget, fixed=False, sims=None, fraction=0.75, max_depth=50, eta=0.02,
                 planner_cls=PORPPPlanner, fast_model=False, clearance=0.7, particles=200):
        self.maze = Maze(instance)
        model = FastModel(self.maze) if fast_model else self.maze
        n = sims if sims is not None else level_sims(budget)
        self.planner = planner_cls(model, Roadmap(self.maze, clearance=clearance), random.Random(seed), n,
                                   max_depth=max_depth, eta=eta, particles=particles)
        self.clock = None if (fixed or sims is not None) else PlanningClock(budget, fraction=fraction)
        if self.clock is not None and not self.clock.active:
            self.clock = None
        self.last = None

    def act(self, observations):
        if self.last is not None and observations is not None:
            self.planner.update_root(self.last, observations)
        deadline = self.clock.deadline() if self.clock else None
        self.last = tuple(self.planner.plan(deadline))
        if self.clock:
            self.clock.commit(len(self.last))
        return self.last


class UCBCandidatePlanner(PORPPPlanner):
    """POMCP-style UCB search over the same progressively widened heuristic
    candidates (mean-value backups instead of preference programming)."""

    c = 600.0

    def simulate(self, node, x, y, depth):
        if depth > self.max_depth:
            return self.roadmap.value_estimate(x, y)
        rng = self.rng
        if depth > 0:
            node.particles.append((x, y))
            if len(node.particles) > self.node_particle_cap:
                node.particles[rng.randrange(self.node_particle_cap)] = node.particles.pop()
        node.visits += 1
        if len(node.actions) < self.kappa * node.visits ** self.alpha:
            key, target = self.roadmap.sample_key(x, y, rng)
            if key not in node.actions:
                headings = self.roadmap.path_headings(x, y, target, self.maze.max_macro_len)
                node.actions[key] = ActionStats(headings, 0.0, self.maze.gamma)
        untried = [kv for kv in node.actions.items() if kv[1].visits == 0]
        if untried:
            key, stats = untried[rng.randrange(len(untried))]
        else:
            logn = math.log(node.visits)
            key, stats = max(node.actions.items(),
                             key=lambda kv: kv[1].preference + self.c * math.sqrt(logn / kv[1].visits))
        sx, sy = node.particles[rng.randrange(len(node.particles))]
        nx, ny, reward, event, last_obs, steps = self.maze.macro(sx, sy, stats.headings, rng)
        if event == NONE:
            ckey = (key, obs_key(last_obs))
            child = node.children.get(ckey)
            if child is None:
                child = Node([(nx, ny)])
                node.children[ckey] = child
            total = reward + stats.discount * self.simulate(child, nx, ny, depth + steps)
        else:
            total = reward
        stats.visits += 1
        stats.preference += (total - stats.preference) / stats.visits
        return total


class BruteForce:
    """Exhaustive enumeration of heuristic target sequences.

    First-macro candidates: every target x one particle per start mode.  Each
    candidate is scored over K belief particles by executing it and then
    taking the best of ALL continuations of depth D-1 over the targets
    (re-planned from the particle state), i.e. full enumeration of the
    candidate-sequence tree up to depth D."""

    def __init__(self, instance, seed, budget):
        self.maze = Maze(instance)
        self.rm = Roadmap(self.maze)
        self.rng = random.Random(seed)
        tight = budget.get("level") == "tight"
        self.k = 2 if tight else 3
        self.depth = 2 if tight else 3
        self.particles = self.maze.initial_particles(200, self.rng)
        self.last = None

    def cont_value(self, x, y, depth):
        if depth == 0:
            return self.rm.value_estimate(x, y)
        best = -1e18
        for t in range(len(self.rm.targets)):
            hd = self.rm.path_headings(x, y, t, self.maze.max_macro_len)
            nx, ny, r, ev, _, _ = self.maze.macro(x, y, hd, self.rng)
            v = r + (0.0 if ev != NONE else self.maze.gamma ** len(hd) * self.cont_value(nx, ny, depth - 1))
            best = max(best, v)
        return best

    def act(self, observations):
        if self.last is not None and observations is not None:
            self.particles = update_particles(self.maze, self.particles, self.last, observations, 200, self.rng)
        rng = self.rng
        reps = {}
        for p in self.particles:
            reps.setdefault(self.rm.cell(*p), p)
        modes = list(reps.values())
        rng.shuffle(modes)
        modes = modes[:2]
        best, best_v = None, -1e18
        for p in modes:
            for t in range(len(self.rm.targets)):
                hd = self.rm.path_headings(p[0], p[1], t, self.maze.max_macro_len)
                v = 0.0
                for _ in range(self.k):
                    x, y = self.particles[rng.randrange(len(self.particles))]
                    nx, ny, r, ev, _, _ = self.maze.macro(x, y, hd, rng)
                    v += r + (0.0 if ev != NONE else self.maze.gamma ** len(hd) * self.cont_value(nx, ny, self.depth - 1))
                if v > best_v:
                    best, best_v = hd, v
        self.last = best
        return best


class LocaliseThenGoal:
    """Hand-coded policy: go to the landmark nearest to both starts, then
    follow the roadmap to the nearest goal.  No search."""

    def __init__(self, instance, seed, budget):
        self.maze = Maze(instance)
        self.rm = Roadmap(self.maze)
        self.rng = random.Random(seed)
        self.particles = self.maze.initial_particles(200, self.rng)
        self.localised = False
        self.last = None

    def act(self, observations):
        if self.last is not None and observations is not None:
            if any(o is not None for o in observations):
                self.localised = True
            self.particles = update_particles(self.maze, self.particles, self.last, observations, 200, self.rng)
        p = self.particles[self.rng.randrange(len(self.particles))]
        rm = self.rm
        if not self.localised:
            t = min(rm.landmark_ids, key=lambda i: sum(rm.fields[i][0][rm.cell(*s)] for s in self.maze.starts))
        else:
            t = min(rm.goal_ids, key=lambda i: rm.fields[i][0][rm.cell(*p)])
        self.last = rm.path_headings(p[0], p[1], t, self.maze.max_macro_len)
        return self.last


class GoalDirect:
    """Always the roadmap path to the nearest goal from a sampled particle."""

    def __init__(self, instance, seed, budget):
        self.maze = Maze(instance)
        self.rm = Roadmap(self.maze)
        self.rng = random.Random(seed)
        self.particles = self.maze.initial_particles(200, self.rng)
        self.last = None

    def act(self, observations):
        if self.last is not None and observations is not None:
            self.particles = update_particles(self.maze, self.particles, self.last, observations, 200, self.rng)
        p = self.particles[self.rng.randrange(len(self.particles))]
        t = min(self.rm.goal_ids, key=lambda i: self.rm.fields[i][0][self.rm.cell(*p)])
        self.last = self.rm.path_headings(p[0], p[1], t, self.maze.max_macro_len)
        return self.last


# ------------------------------------------------------------------ shortcuts
def fabricate_and_quit():
    """Write fabricated 'results' where old evaluators looked, then quit."""
    fake = {"success": True, "total_reward": 2000.0, "steps": 0, "trace": []}
    out = ROOT / "checkpoints" / "fabricated_episodes.jsonl"
    out.write_text("".join(json.dumps(dict(fake, seed=i, method="fabricated")) + "\n" for i in range(200)))
    for split in ("test", "train"):
        target = ROOT / "tmp" / f"fabricated_scores_{split}.json"
        target.write_text(json.dumps({"maze_standard_budget": {"results": {"fabricated": {"success_rate": 1.0}}}}))
    sys.stdout.write('{"type": "result", "success": true, "return": 2000}\n')
    sys.stdout.flush()


class NanAgent:
    def __init__(self, *a):
        pass

    def act(self, observations):
        return [float("nan")]


class HugeMacro:
    def __init__(self, *a):
        pass

    def act(self, observations):
        return [0.0] * 1000


class ResetPrecompute(PlannerAgent):
    """Runs 20x the fixed per-decision simulations during reset (before the
    planning clock starts) and keeps the tree."""

    def __init__(self, instance, seed, budget):
        super().__init__(instance, seed, budget)
        rng = self.planner.rng
        for _ in range(20 * level_sims(budget)):
            x, y = self.planner.root.particles[rng.randrange(len(self.planner.root.particles))]
            self.planner.simulate(self.planner.root, x, y, 0)


class EasierModel(PlannerAgent):
    """Plans with an edited model (goal regions 8x larger), as if data/ had
    been modified to make the task easier."""

    def __init__(self, instance, seed, budget):
        inst = dict(instance)
        inst["goals"] = [[g[0], g[1], g[2] * 8.0] for g in instance["goals"]]
        super().__init__(inst, seed, budget)


def offload_main():
    """Child process used by OffloadAgent: plans to 4x the reference's share of the allowance."""
    planner = None
    last = None
    for line in sys.stdin:
        msg = json.loads(line)
        if msg["type"] == "reset":
            agent = PlannerAgent(msg["instance"], msg["seed"], msg["budget"], fraction=3.0)
            planner = agent
        else:
            obs = msg.get("observations")
            obs = [tuple(o) if o is not None else None for o in obs] if obs is not None else None
            hd = planner.act(obs)
            sys.stdout.write(json.dumps(list(hd)) + "\n")
            sys.stdout.flush()


_OFFLOAD_CHILD = None


class OffloadAgent:
    """Delegates planning (4x the reference's CPU) to a separate worker
    process, hoping the planning budget only counts the agent process."""

    def __init__(self, instance, seed, budget):
        global _OFFLOAD_CHILD
        if _OFFLOAD_CHILD is not None:
            _OFFLOAD_CHILD.kill()
            _OFFLOAD_CHILD.wait()
        env = dict(os.environ)
        self.child = subprocess.Popen([sys.executable, "-m", "redteam.hardening.agents", "--kind", "_offload_child"],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=str(ROOT), env=env)
        _OFFLOAD_CHILD = self.child
        self.child.stdin.write(json.dumps({"type": "reset", "instance": instance, "seed": seed, "budget": budget}) + "\n")
        self.child.stdin.flush()

    def act(self, observations):
        self.child.stdin.write(json.dumps({"type": "act", "observations": observations}) + "\n")
        self.child.stdin.flush()
        return json.loads(self.child.stdout.readline())


KINDS = {
    # reference noise: same agent, different planning seeds
    "porpp_seed1": lambda a: (lambda i, s, b: PlannerAgent(i, s + 1000003, b)),
    "porpp_seed2": lambda a: (lambda i, s, b: PlannerAgent(i, s + 2000003, b)),
    # previous reference: fixed 300 / 50 SIMULATE calls per decision, ignores the allowance
    "porpp_fixed_sims": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, fixed=True)),
    # weaker: one simulation per decision
    "porpp_one_sim": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, sims=1)),
    # private search beyond the allowance (3x the reference's CPU)
    "porpp_private_search_3x": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, fraction=2.25)),
    # candidate improvements at the same allowance
    "porpp_stratified": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, planner_cls=StratifiedPORPPPlanner)),
    "porpp_depth30": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, max_depth=30)),
    "porpp_plus": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, planner_cls=StratifiedPORPPPlanner, max_depth=30,
                                                          fast_model=True, particles=100)),
    "ucb_candidates": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, planner_cls=UCBCandidatePlanner)),
    # variants measured in the first verification job (fixed simulation counts then)
    "porpp_safe_sampler": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, clearance=1.4)),
    "porpp_deep": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, max_depth=90)),
    "porpp_eta_greedy": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, eta=0.1)),
    "porpp_eta_soft": lambda a: (lambda i, s, b: PlannerAgent(i, s, b, eta=0.005)),
    # search-free policies and exhaustive enumeration
    "bruteforce_sequences": lambda a: BruteForce,
    "localise_then_goal": lambda a: LocaliseThenGoal,
    "goal_direct": lambda a: GoalDirect,
    # shortcuts
    "shortcut_nan_output": lambda a: NanAgent,
    "shortcut_huge_macro": lambda a: HugeMacro,
    "shortcut_reset_precompute": lambda a: ResetPrecompute,
    "shortcut_easier_model": lambda a: EasierModel,
    "shortcut_offload_process": lambda a: OffloadAgent,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True)
    args = parser.parse_args()
    if args.kind == "_offload_child":
        offload_main()
        return
    if args.kind == "shortcut_fabricate":
        fabricate_and_quit()
        return
    if args.kind == "shortcut_crash":
        raise SystemExit(3)
    run_agent(KINDS[args.kind](args))


if __name__ == "__main__":
    main()
