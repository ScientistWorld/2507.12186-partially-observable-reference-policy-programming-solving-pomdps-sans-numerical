"""Partially Observable Reference Policy Programming (PORPP).

This implements the paper's online asynchronous preference-programming solver:
tree histories with particle beliefs, progressive widening over macro actions,
softmax sampling from preferences, and Algorithm 2 style sampled backups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import argparse
import json
import math
import random
import time
from pathlib import Path
from typing import Dict, List, Optional

from data.maze_pomdp import MacroAction, MazePOMDP, MazeState, initial_particles


@dataclass
class ActionStats:
    action: MacroAction
    visits: int = 0
    reward_mean: float = 0.0
    downstream_mean: float = 0.0
    preference: float = 0.0


@dataclass
class Node:
    particles: List[MazeState]
    visits: int = 0
    value: float = 0.0
    actions: Dict[str, ActionStats] = field(default_factory=dict)
    children: Dict[tuple, "Node"] = field(default_factory=dict)


class PORPPPlanner:
    def __init__(
        self,
        env: MazePOMDP,
        particles: List[MazeState],
        rng: random.Random,
        simulations_per_step: int = 250,
        max_depth: int = 18,
        eta: float = 0.45,
        kappa_action: float = 8.0,
        alpha_action: float = 0.55,
    ):
        self.env = env
        self.rng = rng
        self.simulations_per_step = simulations_per_step
        self.max_depth = max_depth
        self.eta = eta
        self.kappa_action = kappa_action
        self.alpha_action = alpha_action
        self.root = Node(list(particles))

    def plan(self) -> MacroAction:
        for _ in range(self.simulations_per_step):
            if not self.root.particles:
                break
            state = self.rng.choice(self.root.particles)
            self.simulate(self.root, state, 0)
        if not self.root.actions:
            self._maybe_add_action(self.root, self.rng.choice(self.root.particles))
        return max(self.root.actions.values(), key=lambda a: a.preference).action

    def update_root(self, action: MacroAction, observation, particle_count: int) -> None:
        key = (self.env.action_key(action), observation)
        if key in self.root.children:
            child = self.root.children[key]
            child.particles = self.env.resample_particles(self.root.particles, action, observation, particle_count, self.rng)
            self.root = child
        else:
            self.root = Node(self.env.resample_particles(self.root.particles, action, observation, particle_count, self.rng))

    def simulate(self, node: Node, state: MazeState, depth: int) -> float:
        if depth > self.max_depth or state.terminal:
            return self.env.value_heuristic(state)
        if depth > 0:
            node.particles.append(state)
            if len(node.particles) > 200:
                node.particles.pop(0)
        node.visits += 1
        self._maybe_add_action(node, state)
        if not node.actions:
            self._maybe_add_action(node, state, force=True)

        action_stats = self._sample_preference_softmax(node)
        sampled_state = self.rng.choice(node.particles) if node.particles else state
        next_state, observation, reward, _ = self.env.macro_step(sampled_state, action_stats.action, self.rng)
        child_key = (self.env.action_key(action_stats.action), observation)
        child = node.children.get(child_key)
        if child is None:
            child = Node([next_state])
            node.children[child_key] = child

        action_stats.visits += 1
        n = action_stats.visits
        downstream = self.simulate(child, next_state, depth + action_stats.action.length)
        action_stats.reward_mean += (reward - action_stats.reward_mean) / n
        action_stats.downstream_mean += (downstream - action_stats.downstream_mean) / n

        # Algorithm 2 line 21: Psi <- Psi - V(h) + R(ha) + gamma^|a| D(ha).
        action_stats.preference = (
            action_stats.preference
            - node.value
            + action_stats.reward_mean
            + (self.env.config.gamma ** action_stats.action.length) * action_stats.downstream_mean
        )
        node.value = self._logsumexp_value(node)
        return node.value

    def _maybe_add_action(self, node: Node, state: MazeState, force: bool = False) -> None:
        threshold = self.kappa_action * (max(1, node.visits) ** self.alpha_action)
        if not force and len(node.actions) >= threshold:
            return
        for action in self.env.heuristic_actions(state, self.rng):
            key = self.env.action_key(action)
            if key not in node.actions:
                node.actions[key] = ActionStats(action=action)
                return

    def _sample_preference_softmax(self, node: Node) -> ActionStats:
        actions = list(node.actions.values())
        if len(actions) == 1:
            return actions[0]
        max_pref = max(a.preference for a in actions)
        weights = [math.exp(self.eta * (a.preference - max_pref)) for a in actions]
        total = sum(weights)
        draw = self.rng.random() * total
        acc = 0.0
        for action, weight in zip(actions, weights):
            acc += weight
            if draw <= acc:
                return action
        return actions[-1]

    def _logsumexp_value(self, node: Node) -> float:
        if not node.actions:
            return 0.0
        prefs = [a.preference for a in node.actions.values()]
        max_pref = max(prefs)
        return max_pref + math.log(sum(math.exp(self.eta * (p - max_pref)) for p in prefs)) / self.eta


def run_episode(seed: int, simulations: int, particle_count: int, max_steps: int) -> dict:
    rng = random.Random(seed)
    env = MazePOMDP()
    true_state = env.sample_initial_state(rng)
    planner = PORPPPlanner(env, initial_particles(env.config, particle_count, rng), rng, simulations_per_step=simulations)
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
        "method": "porpp",
        "simulations": simulations,
        "particles": particle_count,
        "success": bool(true_state.success),
        "total_reward": total_reward,
        "steps": steps,
        "trace": trace,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--simulations", type=int, default=250)
    parser.add_argument("--particles", type=int, default=80)
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("checkpoints/porpp_episodes.jsonl"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for i in range(args.episodes):
            result = run_episode(args.seed + i, args.simulations, args.particles, args.max_steps)
            f.write(json.dumps(result) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
