"""POMCP baseline (Silver and Veness, 2010) as configured in the paper.

Particle-belief Monte Carlo tree search with UCB1 action selection that
exhaustively enumerates a fixed set of 16 macro actions made of equally spaced
directional vectors (each repeated for the maximum macro length), as in the
paper's benchmark protocol.  It shares the generative model, depth cut-off,
leaf value estimate, particle filter and per-decision simulation counts with
the PORPP reference so that the comparison isolates the search scheme.

Run as an agent:  python -m baseline.pomcp
"""

from __future__ import annotations

import argparse
import math
import random
from typing import Dict, List, Tuple

from data.agent_protocol import run_agent
from data.maze2d import NONE, Maze, Roadmap, update_particles

SIMULATIONS = {"standard": 300, "tight": 50}


def obs_key(obs):
    if obs is None:
        return None
    return (int(round(obs[0])), int(round(obs[1])))


class Node:
    __slots__ = ("particles", "visits", "counts", "values", "children")

    def __init__(self, particles, n_actions):
        self.particles = particles
        self.visits = 0
        self.counts = [0] * n_actions
        self.values = [0.0] * n_actions
        self.children: Dict[tuple, "Node"] = {}


class POMCP:
    def __init__(self, instance: dict, seed: int, budget: dict, particles: int = 200, max_depth: int = 50,
                 exploration: float = 1000.0, n_directions: int = 16, simulations: int = 0):
        self.maze = Maze(instance)
        self.roadmap = Roadmap(self.maze)
        self.rng = random.Random(seed)
        self.count = particles
        self.max_depth = max_depth
        self.c = exploration
        self.sims = simulations or SIMULATIONS.get(budget.get("level", "standard"), SIMULATIONS["standard"])
        L = self.maze.max_macro_len
        self.actions: List[Tuple[float, ...]] = [
            tuple(round(2.0 * math.pi * i / n_directions, 4) for _ in range(L)) for i in range(n_directions)
        ]
        self.discounts = [self.maze.gamma ** len(a) for a in self.actions]
        self.root = Node(self.maze.initial_particles(particles, self.rng), len(self.actions))
        self.last = None

    def act(self, observations):
        if self.last is not None and observations is not None:
            last_obs = None
            for o in observations:
                if o is not None:
                    last_obs = o
            particles = update_particles(self.maze, self.root.particles, self.actions[self.last], observations, self.count, self.rng)
            child = self.root.children.get((self.last, obs_key(last_obs)))
            if child is None:
                child = Node(particles, len(self.actions))
            else:
                child.particles = particles
            self.root = child
        rng = self.rng
        for _ in range(self.sims):
            x, y = self.root.particles[rng.randrange(len(self.root.particles))]
            self.simulate(self.root, x, y, 0)
        best = max(range(len(self.actions)), key=lambda a: (self.root.counts[a] > 0, self.root.values[a]))
        self.last = best
        return self.actions[best]

    def simulate(self, node: Node, x: float, y: float, depth: int) -> float:
        if depth > self.max_depth:
            return self.roadmap.value_estimate(x, y)
        rng = self.rng
        if depth > 0:
            node.particles.append((x, y))
            if len(node.particles) > 64:
                node.particles[rng.randrange(64)] = node.particles.pop()
        node.visits += 1
        untried = [a for a, n in enumerate(node.counts) if n == 0]
        if untried:
            a = untried[rng.randrange(len(untried))]
        else:
            logn = math.log(node.visits)
            c = self.c
            a = max(range(len(self.actions)), key=lambda i: node.values[i] + c * math.sqrt(logn / node.counts[i]))
        sx, sy = node.particles[rng.randrange(len(node.particles))]
        nx, ny, reward, event, last_obs, steps = self.maze.macro(sx, sy, self.actions[a], rng)
        if event == NONE:
            key = (a, obs_key(last_obs))
            child = node.children.get(key)
            if child is None:
                child = Node([(nx, ny)], len(self.actions))
                node.children[key] = child
            total = reward + self.discounts[a] * self.simulate(child, nx, ny, depth + steps)
        else:
            total = reward
        node.counts[a] += 1
        node.values[a] += (total - node.values[a]) / node.counts[a]
        return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulations", type=int, default=0)
    parser.add_argument("--exploration", type=float, default=1000.0)
    args = parser.parse_args()
    run_agent(lambda inst, seed, budget: POMCP(inst, seed, budget, simulations=args.simulations,
                                               exploration=args.exploration))


if __name__ == "__main__":
    main()
