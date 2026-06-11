"""Scaled continuous maze POMDP used for the PORPP reproduction.

The original paper evaluates on unreleased 3D/Corsica simulators. This module
provides a small, deterministic-to-construct analogue of the 3D maze: two
possible starts, poor localization except at landmarks, a danger region, macro
actions, and long-horizon rewards. It is shared by methods and baselines.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import random
from typing import Iterable, List, Optional, Sequence, Tuple

Point = Tuple[float, float]
Observation = Optional[Tuple[int, int]]


@dataclass(frozen=True)
class MazeConfig:
    width: float = 20.0
    height: float = 20.0
    step_size: float = 1.0
    process_noise: float = 0.10
    obs_noise: float = 0.15
    gamma: float = 0.99
    max_steps: int = 40
    max_macro_len: int = 5
    step_penalty: float = -5.0
    goal_reward: float = 2000.0
    danger_penalty: float = -1800.0
    starts: Tuple[Point, Point] = ((2.0, 2.0), (2.0, 18.0))
    landmark_a: Point = (6.0, 10.0)
    landmark_b: Point = (13.0, 10.0)
    landmark_radius: float = 1.15
    goal: Point = (18.0, 10.0)
    goal_radius: float = 1.0
    danger: Point = (10.0, 16.5)
    danger_radius: float = 2.4


def maze_config(name: str = "default") -> MazeConfig:
    """Return a named scaled-maze setting.

    The mirrored setting is an additional core-claim check: the unsafe direct
    route is mirrored to the lower start while the observation and action
    structure stays the same.
    """
    if name in {"default", "scaled_maze"}:
        return MazeConfig()
    if name == "mirrored_danger":
        return replace(MazeConfig(), danger=(10.0, 3.5))
    raise ValueError(f"unknown maze scenario: {name}")


@dataclass(frozen=True)
class MazeState:
    x: float
    y: float
    localized: bool = False
    terminal: bool = False
    success: bool = False

    def point(self) -> Point:
        return (self.x, self.y)


@dataclass(frozen=True)
class MacroAction:
    name: str
    target: Point
    avoid_danger: bool = False
    length: int = 5
    is_direction: bool = False


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def initial_particles(config: MazeConfig, count: int, rng: random.Random) -> List[MazeState]:
    particles: List[MazeState] = []
    for i in range(count):
        sx, sy = config.starts[i % len(config.starts)]
        particles.append(
            MazeState(
                sx + rng.gauss(0.0, 0.05),
                sy + rng.gauss(0.0, 0.05),
                localized=False,
            )
        )
    rng.shuffle(particles)
    return particles


class MazePOMDP:
    def __init__(self, config: MazeConfig | None = None):
        self.config = config or MazeConfig()

    def sample_initial_state(self, rng: random.Random) -> MazeState:
        sx, sy = rng.choice(self.config.starts)
        return MazeState(sx + rng.gauss(0.0, 0.05), sy + rng.gauss(0.0, 0.05))

    def heuristic_actions(self, state: MazeState, rng: random.Random) -> List[MacroAction]:
        """Domain sampler analogous to the paper's PRM sampler.

        It proposes landmark-seeking and goal-seeking macro actions using local
        geometric knowledge, but it does not solve the belief problem by itself.
        """
        cfg = self.config
        actions = [
            MacroAction("to_landmark_a", cfg.landmark_a, False, cfg.max_macro_len),
            MacroAction("to_landmark_b", cfg.landmark_b, False, cfg.max_macro_len),
            MacroAction("to_goal_direct", cfg.goal, False, cfg.max_macro_len),
            MacroAction("to_goal_safe", cfg.goal, True, cfg.max_macro_len),
        ]
        # Add one state-dependent option first, similar to sampling a PRM path
        # from a particle toward a sampled objective. The heuristic is purposely
        # suboptimal under poor localization: before landmark contact it often
        # proposes the direct route, which is dangerous for one possible start.
        if not state.localized:
            primary = actions[2] if rng.random() < 0.85 else rng.choice(actions[:2])
        else:
            primary = actions[3] if rng.random() < 0.75 else rng.choice(actions)
        return [primary] + [a for a in actions if a.name != primary.name]

    def representative_actions(self) -> List[MacroAction]:
        cfg = self.config
        return [
            MacroAction("to_landmark_a", cfg.landmark_a, False, cfg.max_macro_len),
            MacroAction("to_landmark_b", cfg.landmark_b, False, cfg.max_macro_len),
            MacroAction("to_goal_direct", cfg.goal, False, cfg.max_macro_len),
            MacroAction("to_goal_safe", cfg.goal, True, cfg.max_macro_len),
        ]

    def directional_actions(self, count: int = 16) -> List[MacroAction]:
        """Fixed macro-action set for POMCP-style exhaustive expansion.

        The paper's POMCP baseline does not use the domain-specific PRM
        candidate sampler; it expands equally spaced directional macro actions.
        This 2D analogue keeps that separation from the PORPP/RefPol sampler.
        """
        cfg = self.config
        actions: List[MacroAction] = []
        for i in range(count):
            theta = 2.0 * math.pi * i / count
            actions.append(
                MacroAction(
                    name=f"dir_{i:02d}",
                    target=(math.cos(theta), math.sin(theta)),
                    avoid_danger=False,
                    length=cfg.max_macro_len,
                    is_direction=True,
                )
            )
        return actions

    def macro_step(
        self, state: MazeState, action: MacroAction, rng: random.Random
    ) -> Tuple[MazeState, Observation, float, bool]:
        if state.terminal:
            return state, None, 0.0, True

        cfg = self.config
        s = state
        discounted_reward = 0.0
        discount = 1.0
        observation: Observation = None

        target = action.target
        for _ in range(max(1, action.length)):
            if s.terminal:
                break
            waypoint = (s.x + target[0], s.y + target[1]) if action.is_direction else target
            if (not action.is_direction) and action.avoid_danger and distance(s.point(), cfg.danger) < 6.0:
                bypass_y = cfg.goal[1] - 2.5 if cfg.danger[1] > cfg.goal[1] else cfg.goal[1] + 2.5
                waypoint = (cfg.danger[0] - 1.5, bypass_y)
            dx, dy = waypoint[0] - s.x, waypoint[1] - s.y
            norm = max(math.hypot(dx, dy), 1e-9)
            nx = s.x + cfg.step_size * dx / norm + rng.gauss(0.0, cfg.process_noise)
            ny = s.y + cfg.step_size * dy / norm + rng.gauss(0.0, cfg.process_noise)
            nx = min(cfg.width, max(0.0, nx))
            ny = min(cfg.height, max(0.0, ny))

            localized = s.localized
            reward = cfg.step_penalty
            terminal = False
            success = False
            p = (nx, ny)
            if distance(p, cfg.danger) <= cfg.danger_radius:
                reward += cfg.danger_penalty
                terminal = True
            if distance(p, cfg.goal) <= cfg.goal_radius:
                reward += cfg.goal_reward
                terminal = True
                success = True
            if distance(p, cfg.landmark_a) <= cfg.landmark_radius or distance(p, cfg.landmark_b) <= cfg.landmark_radius:
                localized = True
                observation = (round(nx + rng.gauss(0.0, cfg.obs_noise)), round(ny + rng.gauss(0.0, cfg.obs_noise)))

            discounted_reward += discount * reward
            discount *= cfg.gamma
            s = MazeState(nx, ny, localized=localized, terminal=terminal, success=success)

        return s, observation, discounted_reward, s.terminal

    def resample_particles(
        self,
        prior_particles: Sequence[MazeState],
        action: MacroAction,
        observation: Observation,
        count: int,
        rng: random.Random,
    ) -> List[MazeState]:
        candidates: List[MazeState] = []
        attempts = max(200, count * 12)
        for _ in range(attempts):
            base = rng.choice(prior_particles)
            ns, obs, _, _ = self.macro_step(base, action, rng)
            if self._obs_compatible(obs, observation):
                candidates.append(ns)
                if len(candidates) >= count:
                    break
        if not candidates:
            for _ in range(count):
                base = rng.choice(prior_particles)
                ns, _, _, _ = self.macro_step(base, action, rng)
                candidates.append(ns)
        while len(candidates) < count:
            candidates.append(rng.choice(candidates))
        return candidates[:count]

    def _obs_compatible(self, observed: Observation, target: Observation) -> bool:
        if target is None:
            return observed is None
        if observed is None:
            return False
        return abs(observed[0] - target[0]) <= 1 and abs(observed[1] - target[1]) <= 1

    def value_heuristic(self, state: MazeState) -> float:
        if state.terminal:
            return 0.0
        optimistic_steps = max(0.0, distance(state.point(), self.config.goal) / self.config.step_size)
        danger_margin = max(0.0, 5.0 - distance(state.point(), self.config.danger))
        danger_penalty = 35.0 * danger_margin
        return self.config.goal_reward * (self.config.gamma ** optimistic_steps) + self.config.step_penalty * optimistic_steps - danger_penalty

    def action_key(self, action: MacroAction) -> str:
        return action.name

    def action_by_key(self, key: str) -> MacroAction:
        for action in self.representative_actions():
            if action.name == key:
                return action
        raise KeyError(key)
