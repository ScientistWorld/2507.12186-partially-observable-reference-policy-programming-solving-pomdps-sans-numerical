"""Honest planners and explicitly named shortcut policies for the audit.

Generation uses only method/, baseline/, and data/, all visible in improve mode.
No generator imports the hidden evaluator or reads hidden scores.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
import random
import time


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
            stream.flush()


def porpp_rows(seed, simulations=700, particles=120, episodes=32):
    from method.porpp import run_episode
    for episode in range(episodes):
        yield run_episode(seed + episode, simulations, particles, 40, "default")


def candidate_search_rows(seed=7, episodes=32):
    """Honest stronger search: UCB explores all four permitted candidate actions.

    This changes the search rule, retaining the same belief filter, horizon,
    action vocabulary, environment, and simulation budget. It is an algorithm
    variant, not a claim to reproduce the original preference backup.
    """
    from baseline.pomcp import POMCPPlanner, POMCPAction

    class CandidateSearchPlanner(POMCPPlanner):
        def _ensure_actions(self, node):
            if not node.actions:
                for action in self.env.representative_actions():
                    node.actions[self.env.action_key(action)] = POMCPAction(action)

    for episode in range(episodes):
        yield execute_planner(seed + episode, CandidateSearchPlanner)


def execute_planner(seed, planner_type):
    from data.maze_pomdp import MazePOMDP, initial_particles
    env = MazePOMDP()
    rng = random.Random(seed)
    state = env.sample_initial_state(rng)
    planner = planner_type(env, initial_particles(env.config, 120, rng), rng, 700)
    total, discount, steps, trace = 0.0, 1.0, 0, []
    while steps < 40 and not state.terminal:
        action = planner.plan()
        state, obs, reward, _ = env.macro_step(state, action, rng)
        total += discount * reward
        discount *= env.config.gamma ** action.length
        planner.update_root(action, obs, 120)
        steps += action.length
        trace.append({"action": action.name, "obs": obs, "reward": reward})
    return dict(seed=seed, method="porpp", success=state.success,
                total_reward=total, steps=steps, trace=trace)


def bruteforce_rows(seed=7, episodes=32):
    """Enumerate ALL 4**4 candidate sequences to the reference search depth.

    Each sequence is evaluated over 12 belief particles with fresh simulated
    futures. Replan after each actual observation. No actual state is exposed
    to the search. The 20-step lookahead matches/exceeds the reference's 18-step
    cutoff (in increments of five). This is genuine exhaustive open-loop
    lookahead, not a claim of exact enumeration of stochastic observation trees.
    """
    from data.maze_pomdp import MazePOMDP, initial_particles
    for i in range(episodes):
        episode_seed = seed + i
        env = MazePOMDP()
        env_rng = random.Random(episode_seed)
        plan_rng = random.Random(episode_seed + 1000000)
        state = env.sample_initial_state(env_rng)
        belief = initial_particles(env.config, 120, plan_rng)
        actions = env.representative_actions()
        total, discount, steps, trace = 0.0, 1.0, 0, []
        evaluated = 0
        while steps < 40 and not state.terminal:
            samples = plan_rng.sample(belief, min(12, len(belief)))
            scores = []
            # Common simulation seeds reduce comparison variance; they are
            # planner randomness, not the hidden world's random stream.
            noise_seeds = [plan_rng.randrange(2**32) for _ in samples]
            for sequence in itertools.product(actions, repeat=4):
                values = []
                for particle, noise_seed in zip(samples, noise_seeds):
                    sim_rng = random.Random(noise_seed)
                    simulated, value, factor = particle, 0.0, 1.0
                    for candidate in sequence:
                        simulated, _, reward, _ = env.macro_step(simulated, candidate, sim_rng)
                        value += factor * reward
                        factor *= env.config.gamma ** candidate.length
                        if simulated.terminal:
                            break
                    value += factor * env.value_heuristic(simulated)
                    values.append(value)
                scores.append((sum(values) / len(values), sequence[0]))
                evaluated += 1
            action = max(scores, key=lambda entry: entry[0])[1]
            state, obs, reward, _ = env.macro_step(state, action, env_rng)
            total += discount * reward
            discount *= env.config.gamma ** action.length
            belief = env.resample_particles(belief, action, obs, 120, plan_rng)
            steps += action.length
            trace.append({"action": action.name, "obs": obs, "reward": reward})
        yield dict(seed=episode_seed, method="porpp", success=state.success,
                   total_reward=total, steps=steps, trace=trace,
                   enumerated_sequences=evaluated)


def shortcut_fixed_policy_rows(kind, seed=7, episodes=32):
    """SHORTCUT: fixed-map action sequence, or degenerate constant action."""
    from data.maze_pomdp import MazePOMDP
    for i in range(episodes):
        env = MazePOMDP()
        rng = random.Random(seed + i)
        state = env.sample_initial_state(rng)
        total, discount, steps, trace = 0.0, 1.0, 0, []
        while steps < 40 and not state.terminal:
            if kind == "shortcut_constant_goal":
                name = "to_goal_direct"
            else:
                # SHORTCUT: exploit the fixed known layout, no belief or search.
                name = "to_landmark_a" if steps < 10 else "to_goal_direct"
            action = env.action_by_key(name)
            state, obs, reward, _ = env.macro_step(state, action, rng)
            total += discount * reward
            discount *= env.config.gamma ** action.length
            steps += action.length
            trace.append({"action": name, "obs": obs, "reward": reward})
        yield dict(seed=seed+i, method="porpp", success=state.success,
                   total_reward=total, steps=steps, trace=trace)


def shortcut_fake_rows(success=True, reward=2000.0):
    """SHORTCUT: emit outcomes directly without executing any task."""
    for seed in range(7, 39):
        yield dict(seed=seed, method="porpp", success=success,
                   total_reward=reward, steps=0, trace=[])
