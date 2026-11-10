"""RefPol baseline (paper Sect. 4.3): no planning.

At every decision it samples one state particle from the current belief and
executes the macro action returned by the heuristic action sampler for that
particle (a truncated roadmap path to a random landmark or goal region).

Run as an agent:  python -m baseline.refpol
"""

from __future__ import annotations

import random

from data.agent_protocol import run_agent
from data.maze2d import Maze, Roadmap, update_particles


class RefPol:
    def __init__(self, instance: dict, seed: int, budget: dict, particles: int = 200):
        self.maze = Maze(instance)
        self.roadmap = Roadmap(self.maze)
        self.rng = random.Random(seed)
        self.count = particles
        self.particles = self.maze.initial_particles(particles, self.rng)
        self.last = None

    def act(self, observations):
        if self.last is not None and observations is not None:
            self.particles = update_particles(self.maze, self.particles, self.last, observations, self.count, self.rng)
        x, y = self.particles[self.rng.randrange(len(self.particles))]
        self.last = self.roadmap.sample_candidate(x, y, self.rng)[1]
        return self.last


if __name__ == "__main__":
    run_agent(RefPol)
