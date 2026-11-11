"""Partially Observable Reference Policy Programming (PORPP), Algorithms 1-2.

Online anytime POMDP planner:

* a history tree whose nodes hold particle beliefs (Alg. 2 line 5);
* progressive widening |children(h)| < kappa * N(h)^alpha, each widening step
  asks the heuristic action sampler for ONE candidate macro action from the
  current particle (Alg. 2 lines 8-13);
* action selection by sampling the softmax of the preferences (line 14);
* the state used for the generative step is resampled from b(h) (line 15);
* sampled running means R(ha), D(ha) and the KL-constrained preference
  backup  Psi(ha) <- Psi(ha) - V(h) + R(ha) + gamma^|a| D(ha)  followed by
  V(h) <- (1/eta) log sum_a exp(eta Psi(ha))  (lines 18-23);
* VALUEHEURISTIC at the depth cut-off (lines 1-3);
* after planning, execute argmax_a Psi(h0 a), update the root to h0 a o and
  add resampled particles consistent with the real observation (Alg. 1).

Planning time: Alg. 1 plans "while time permitting".  The agent plans until a
fixed fraction of the evaluator's announced CPU allowance is used
(data.agent_protocol.PlanningClock); ``--fixed-simulations`` instead runs a
fixed number of SIMULATE calls per decision (deterministic, for diagnostics).

Run as an agent:  python -m method.porpp   (JSON-lines protocol on stdin/stdout,
see briefing/evaluation.md).
"""

from __future__ import annotations

import argparse
import math
import random
from typing import Dict, List, Optional, Tuple

import time

from data.agent_protocol import PlanningClock, run_agent
from data.maze2d import NONE, Maze, Roadmap, update_particles

Point = Tuple[float, float]


class ActionStats:
    __slots__ = ("headings", "visits", "reward_mean", "downstream_mean", "preference", "discount")

    def __init__(self, headings, preference: float, gamma: float):
        self.headings = headings
        self.visits = 0
        self.reward_mean = 0.0
        self.downstream_mean = 0.0
        self.preference = preference
        self.discount = gamma ** len(headings)


class Node:
    __slots__ = ("particles", "visits", "value", "actions", "children")

    def __init__(self, particles: List[Point]):
        self.particles = particles
        self.visits = 0
        self.value = 0.0
        self.actions: Dict[tuple, ActionStats] = {}
        self.children: Dict[tuple, "Node"] = {}


def obs_key(obs) -> Optional[Tuple[int, int]]:
    """Discretised macro observation used to index history-tree children."""
    if obs is None:
        return None
    return (int(round(obs[0])), int(round(obs[1])))


class PORPPPlanner:
    def __init__(
        self,
        maze: Maze,
        roadmap: Roadmap,
        rng: random.Random,
        simulations: int,
        particles: int = 200,
        max_depth: int = 50,
        eta: float = 0.02,
        kappa: float = 2.0,
        alpha: float = 0.5,
        node_particle_cap: int = 64,
    ):
        self.maze = maze
        self.roadmap = roadmap
        self.rng = rng
        self.simulations = simulations
        self.particle_count = particles
        self.max_depth = max_depth
        self.eta = eta
        self.kappa = kappa
        self.alpha = alpha
        self.node_particle_cap = node_particle_cap
        self.root = Node(maze.initial_particles(particles, rng))

    # ------------------------------------------------------------- Algorithm 1
    def plan(self, deadline: Optional[float] = None) -> Tuple[float, ...]:
        """Run SIMULATE from the root until ``deadline`` (process CPU time) or,
        without a deadline, for ``self.simulations`` calls."""
        root = self.root
        rng = self.rng
        clock = time.process_time
        n = 0
        while True:
            if deadline is None:
                if n >= self.simulations:
                    break
            elif n >= 1 and clock() >= deadline:
                break
            x, y = root.particles[rng.randrange(len(root.particles))]
            self.simulate(root, x, y, 0)
            n += 1
        self.last_simulations = n
        visited = [a for a in root.actions.values() if a.visits > 0]
        if not visited:
            x, y = root.particles[rng.randrange(len(root.particles))]
            return self.roadmap.sample_candidate(x, y, rng)[1]
        return max(visited, key=lambda a: a.preference).headings

    def update_root(self, headings, observations) -> None:
        last = None
        for o in observations:
            if o is not None:
                last = o
        akey = None
        for key, stats in self.root.actions.items():
            if stats.headings == tuple(headings):
                akey = key
                break
        particles = update_particles(self.maze, self.root.particles, headings, observations, self.particle_count, self.rng)
        child = self.root.children.get((akey, obs_key(last))) if akey is not None else None
        if child is None:
            child = Node(particles)
        else:
            child.particles = particles
        self.root = child

    # ------------------------------------------------------------- Algorithm 2
    def simulate(self, node: Node, x: float, y: float, depth: int) -> float:
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
                if node.actions:
                    init = node.value
                else:
                    init = self.roadmap.value_estimate(x, y)
                    node.value = init
                node.actions[key] = ActionStats(headings, init, self.maze.gamma)
        key, stats = self._sample_softmax(node)
        sx, sy = node.particles[rng.randrange(len(node.particles))]
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

    def _sample_softmax(self, node: Node):
        items = list(node.actions.items())
        if len(items) == 1:
            return items[0]
        eta = self.eta
        top = max(s.preference for _, s in items)
        weights = [math.exp(eta * (s.preference - top)) for _, s in items]
        draw = self.rng.random() * sum(weights)
        acc = 0.0
        for item, weight in zip(items, weights):
            acc += weight
            if draw <= acc:
                return item
        return items[-1]

    def _log_sum_exp(self, node: Node) -> float:
        eta = self.eta
        prefs = [s.preference for s in node.actions.values()]
        top = max(prefs)
        return top + math.log(sum(math.exp(eta * (p - top)) for p in prefs)) / eta


# ------------------------------------------------------------------ agent loop
# Fixed SIMULATE calls per decision per budget level (only with --fixed-simulations).
BUDGET_SIMULATIONS = {"standard": 300, "tight": 50}


class PORPPAgent:
    def __init__(self, instance: dict, seed: int, budget: dict, args):
        maze = Maze(instance)
        level = budget.get("level", "standard")
        sims = args.simulations or BUDGET_SIMULATIONS.get(level, BUDGET_SIMULATIONS["standard"])
        self.planner = PORPPPlanner(maze, Roadmap(maze), random.Random(seed + args.seed_offset), sims,
                                    particles=args.particles, max_depth=args.max_depth, eta=args.eta,
                                    kappa=args.kappa, alpha=args.alpha)
        self.last = None
        fixed = args.fixed_simulations or args.simulations
        self.clock = None if fixed else PlanningClock(budget, fraction=args.budget_fraction)
        if self.clock is not None and not self.clock.active:
            self.clock = None

    def act(self, observations):
        if self.last is not None and observations is not None:
            self.planner.update_root(self.last, observations)
        deadline = self.clock.deadline() if self.clock else None
        self.last = tuple(self.planner.plan(deadline))
        if self.clock:
            self.clock.commit(len(self.last))
        return self.last


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-fraction", type=float, default=0.75,
                        help="fraction of the evaluator's CPU allowance to plan for")
    parser.add_argument("--fixed-simulations", action="store_true",
                        help="ignore the CPU allowance; run BUDGET_SIMULATIONS[level] SIMULATE calls per decision")
    parser.add_argument("--simulations", type=int, default=0, help="fixed SIMULATE calls per decision")
    parser.add_argument("--particles", type=int, default=200)
    parser.add_argument("--max-depth", type=int, default=50)
    parser.add_argument("--eta", type=float, default=0.02)
    parser.add_argument("--kappa", type=float, default=2.0)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--seed-offset", type=int, default=0)
    args = parser.parse_args()
    run_agent(lambda instance, seed, budget: PORPPAgent(instance, seed, budget, args))


if __name__ == "__main__":
    main()
