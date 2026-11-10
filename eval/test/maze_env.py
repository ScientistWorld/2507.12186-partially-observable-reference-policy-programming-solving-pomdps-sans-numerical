"""Evaluator-owned copy of the maze dynamics (the "real world").

Arithmetic is identical to the public generative model in data/maze2d.py, so
an honest planner's model is exact, but scoring never depends on any file a
method can edit.
"""

from __future__ import annotations

import math

NONE, DANGER, GOAL = 0, 1, 2
WORST_RETURN = -500.0


class TrueMaze:
    def __init__(self, spec: dict):
        rows = spec["grid"]
        self.height = len(rows)
        self.width = len(rows[0])
        if any(len(r) != self.width for r in rows):
            raise ValueError("ragged grid")
        self.blocked = [ch == "#" for row in rows for ch in row]
        self.starts = [(float(p[0]), float(p[1])) for p in spec["starts"]]
        self.gamma = float(spec["gamma"])
        self.step_penalty = float(spec["step_penalty"])
        self.goal_reward = float(spec["goal_reward"])
        self.danger_penalty = float(spec["danger_penalty"])
        self.step_size = float(spec["step_size"])
        self.noise = float(spec["motion_noise_std"])
        self.max_macro_len = int(spec["max_macro_len"])
        self.horizon = int(spec["horizon"])
        self._danger_r2 = [(float(x), float(y), float(r) * float(r)) for x, y, r in spec["dangers"]]
        self._goal_r2 = [(float(x), float(y), float(r) * float(r)) for x, y, r in spec["goals"]]
        self._land_r2 = [(float(x), float(y), float(r) * float(r)) for x, y, r in spec["landmarks"]]

    def free(self, x: float, y: float) -> bool:
        if x < 0.0 or y < 0.0 or x >= self.width or y >= self.height:
            return False
        return not self.blocked[int(y) * self.width + int(x)]

    def move(self, x: float, y: float, dx: float, dy: float):
        free = self.free
        nx, ny = x + dx, y + dy
        if free(nx, ny) and free(x + 0.5 * dx, y + 0.5 * dy):
            return nx, ny
        if free(nx, y) and free(x + 0.5 * dx, y):
            return nx, y
        if free(x, ny) and free(x, y + 0.5 * dy):
            return x, ny
        return x, y

    def event(self, x: float, y: float) -> int:
        for cx, cy, r2 in self._danger_r2:
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                return DANGER
        for cx, cy, r2 in self._goal_r2:
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                return GOAL
        return NONE

    def at_landmark(self, x: float, y: float) -> bool:
        for cx, cy, r2 in self._land_r2:
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                return True
        return False

    def step(self, x: float, y: float, heading: float, ex: float, ey: float):
        v = self.step_size
        nx, ny = self.move(x, y, v * math.cos(heading) + ex, v * math.sin(heading) + ey)
        ev = self.event(nx, ny)
        if ev == DANGER:
            return nx, ny, self.danger_penalty, ev, None
        if ev == GOAL:
            return nx, ny, self.goal_reward, ev, None
        obs = (round(nx, 3), round(ny, 3)) if self.at_landmark(nx, ny) else None
        return nx, ny, self.step_penalty, ev, obs
