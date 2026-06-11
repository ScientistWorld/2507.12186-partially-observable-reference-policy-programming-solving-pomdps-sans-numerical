"""Reference-policy baseline from the PORPP paper."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from data.maze_pomdp import MazePOMDP, initial_particles, maze_config


def run_episode(seed: int, particle_count: int, max_steps: int, scenario: str) -> dict:
    rng = random.Random(seed)
    env = MazePOMDP(maze_config(scenario))
    true_state = env.sample_initial_state(rng)
    particles = initial_particles(env.config, particle_count, rng)
    total_reward = 0.0
    discount = 1.0
    steps = 0
    trace = []
    while steps < max_steps and not true_state.terminal:
        sampled = rng.choice(particles)
        action = env.heuristic_actions(sampled, rng)[0]
        next_state, observation, reward, done = env.macro_step(true_state, action, rng)
        total_reward += discount * reward
        discount *= env.config.gamma ** action.length
        particles = env.resample_particles(particles, action, observation, particle_count, rng)
        trace.append({"action": action.name, "obs": observation, "reward": reward})
        true_state = next_state
        steps += action.length
        if done:
            break
    return {
        "seed": seed,
        "method": "refpol",
        "scenario": scenario,
        "success": bool(true_state.success),
        "total_reward": total_reward,
        "steps": steps,
        "trace": trace,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--particles", type=int, default=80)
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--scenario", default="default")
    parser.add_argument("--out", type=Path, default=Path("checkpoints/refpol_episodes.jsonl"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for i in range(args.episodes):
            f.write(json.dumps(run_episode(args.seed + i, args.particles, args.max_steps, args.scenario)) + "\n")


if __name__ == "__main__":
    main()
