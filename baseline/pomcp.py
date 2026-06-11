"""POMCP baseline for the scaled maze POMDP.

This is the canonical particle Monte Carlo tree-search baseline used by the
paper, adapted to the finite representative macro actions available in the
scaled maze. Unlike PORPP it enumerates the available actions at every history
node and backs up sampled returns with UCB action selection.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import math
import random
from pathlib import Path
from typing import Dict, List

from data.maze_pomdp import MacroAction, MazePOMDP, MazeState, initial_particles, maze_config


@dataclass
class POMCPAction:
    action: MacroAction
    visits: int = 0
    value: float = 0.0


@dataclass
class POMCPNode:
    particles: List[MazeState] = field(default_factory=list)
    visits: int = 0
    actions: Dict[str, POMCPAction] = field(default_factory=dict)
    children: Dict[tuple, "POMCPNode"] = field(default_factory=dict)


class POMCPPlanner:
    def __init__(
        self,
        env: MazePOMDP,
        particles: List[MazeState],
        rng: random.Random,
        simulations_per_step: int = 350,
        max_depth: int = 18,
        exploration: float = 1400.0,
    ):
        self.env = env
        self.rng = rng
        self.simulations_per_step = simulations_per_step
        self.max_depth = max_depth
        self.exploration = exploration
        self.root = POMCPNode(list(particles))

    def plan(self) -> MacroAction:
        self._ensure_actions(self.root)
        for _ in range(self.simulations_per_step):
            if not self.root.particles:
                break
            state = self.rng.choice(self.root.particles)
            self._simulate(self.root, state, 0)
        return max(self.root.actions.values(), key=lambda stat: stat.value).action

    def update_root(self, action: MacroAction, observation, particle_count: int) -> None:
        key = (self.env.action_key(action), observation)
        prior = self.root.particles
        child = self.root.children.get(key)
        if child is None:
            child = POMCPNode()
        child.particles = self.env.resample_particles(prior, action, observation, particle_count, self.rng)
        self.root = child

    def _simulate(self, node: POMCPNode, state: MazeState, depth: int) -> float:
        if depth > self.max_depth or state.terminal:
            return self.env.value_heuristic(state)
        node.visits += 1
        if depth > 0:
            node.particles.append(state)
            if len(node.particles) > 200:
                node.particles.pop(0)
        self._ensure_actions(node)

        action_stat = self._select_ucb(node)
        sampled_state = self.rng.choice(node.particles) if node.particles else state
        next_state, observation, reward, _ = self.env.macro_step(sampled_state, action_stat.action, self.rng)
        child_key = (self.env.action_key(action_stat.action), observation)
        child = node.children.get(child_key)
        if child is None:
            child = POMCPNode([next_state])
            node.children[child_key] = child

        future = self._simulate(child, next_state, depth + action_stat.action.length)
        total = reward + (self.env.config.gamma ** action_stat.action.length) * future
        action_stat.visits += 1
        action_stat.value += (total - action_stat.value) / action_stat.visits
        return total

    def _ensure_actions(self, node: POMCPNode) -> None:
        if node.actions:
            return
        for action in self.env.directional_actions(16):
            node.actions[self.env.action_key(action)] = POMCPAction(action)

    def _select_ucb(self, node: POMCPNode) -> POMCPAction:
        unvisited = [a for a in node.actions.values() if a.visits == 0]
        if unvisited:
            return self.rng.choice(unvisited)
        log_n = math.log(max(1, node.visits))
        return max(
            node.actions.values(),
            key=lambda a: a.value + self.exploration * math.sqrt(log_n / a.visits),
        )


def run_episode(seed: int, simulations: int, particle_count: int, max_steps: int, scenario: str) -> dict:
    rng = random.Random(seed)
    env = MazePOMDP(maze_config(scenario))
    true_state = env.sample_initial_state(rng)
    planner = POMCPPlanner(env, initial_particles(env.config, particle_count, rng), rng, simulations)
    total_reward = 0.0
    discount = 1.0
    steps = 0
    trace = []
    while steps < max_steps and not true_state.terminal:
        action = planner.plan()
        next_state, observation, reward, done = env.macro_step(true_state, action, rng)
        total_reward += discount * reward
        discount *= env.config.gamma ** action.length
        planner.update_root(action, observation, particle_count)
        trace.append({"action": action.name, "obs": observation, "reward": reward})
        true_state = next_state
        steps += action.length
        if done:
            break
    return {
        "seed": seed,
        "method": "pomcp",
        "scenario": scenario,
        "simulations": simulations,
        "success": bool(true_state.success),
        "total_reward": total_reward,
        "steps": steps,
        "trace": trace,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--simulations", type=int, default=350)
    parser.add_argument("--particles", type=int, default=80)
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=2007)
    parser.add_argument("--scenario", default="default")
    parser.add_argument("--out", type=Path, default=Path("checkpoints/pomcp_episodes.jsonl"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for i in range(args.episodes):
            result = run_episode(args.seed + i, args.simulations, args.particles, args.max_steps, args.scenario)
            f.write(json.dumps(result) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
