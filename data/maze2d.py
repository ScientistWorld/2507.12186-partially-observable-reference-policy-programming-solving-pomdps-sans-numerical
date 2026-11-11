"""Partially observable 2D maze with poor localisation (public problem model).

This is the scaled stand-in for the paper's "3D Maze with Poor Localisation"
(Sect. 4.1).  It keeps the paper's settings wherever they are dimension-free:

* holonomic robot, continuous position, primitive action = any heading of
  fixed speed v = 1, Gaussian motion noise with covariance I * 0.02 * v;
* motion conforms to the walls of a closed maze;
* the robot spawns at one of two known positions with equal probability and
  receives no feedback about which one;
* the only observation is the true position, received when the robot is in
  contact with a landmark; otherwise it observes nothing;
* entering a danger zone ends the episode with -500, entering one of the two
  goal regions ends it with +2000, every other step costs -5, gamma = 0.99;
* macro actions are open-loop sequences of at most 10 primitive headings.

The maze is 2D instead of 3D and a few times shorter (routes of roughly 30-60
primitive steps instead of ~100); layouts are procedurally generated so that
evaluation can use maps a method has never seen.

The module also exposes the domain assets the paper gives its planners:
a generative model (``Maze.macro``), a lattice roadmap that plays the role of
the paper's offline PRM (``Roadmap``) and the paper's heuristic action
sampler built on it (``Roadmap.sample_candidate``), plus a simple particle
belief update.  Nothing here depends on ``method/``.
"""

from __future__ import annotations

import heapq
import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

GAMMA = 0.99
STEP_PENALTY = -5.0
GOAL_REWARD = 2000.0
DANGER_PENALTY = -500.0
STEP_SIZE = 1.0
MOTION_NOISE_STD = math.sqrt(0.02)
MAX_MACRO_LEN = 10
HORIZON = 200
# Lowest achievable discounted return: -5 per step followed by the danger
# penalty always sums to exactly -500 because 5 / (1 - 0.99) = 500.
WORST_RETURN = -500.0

WIDTH = 44
HEIGHT = 30
N_LANDMARKS = 4
N_DANGERS = (12, 18)
DANGER_RADIUS = (1.2, 2.4)
DANGER_GAP = 1.6
N_WALLS = (4, 8)

Point = Tuple[float, float]
Observation = Optional[Tuple[float, float]]

NONE, DANGER, GOAL = 0, 1, 2


def default_parameters() -> dict:
    return {
        "gamma": GAMMA,
        "step_penalty": STEP_PENALTY,
        "goal_reward": GOAL_REWARD,
        "danger_penalty": DANGER_PENALTY,
        "step_size": STEP_SIZE,
        "motion_noise_std": MOTION_NOISE_STD,
        "max_macro_len": MAX_MACRO_LEN,
        "horizon": HORIZON,
    }


class Maze:
    """Generative model of one maze instance (public spec dictionary)."""

    def __init__(self, spec: dict):
        self.spec = spec
        rows = spec["grid"]
        self.height = len(rows)
        self.width = len(rows[0])
        self.blocked = [ch == "#" for row in rows for ch in row]
        self.starts: List[Point] = [(float(p[0]), float(p[1])) for p in spec["starts"]]
        self.goals = [(float(g[0]), float(g[1]), float(g[2])) for g in spec["goals"]]
        self.dangers = [(float(d[0]), float(d[1]), float(d[2])) for d in spec["dangers"]]
        self.landmarks = [(float(m[0]), float(m[1]), float(m[2])) for m in spec["landmarks"]]
        self.gamma = float(spec.get("gamma", GAMMA))
        self.step_penalty = float(spec.get("step_penalty", STEP_PENALTY))
        self.goal_reward = float(spec.get("goal_reward", GOAL_REWARD))
        self.danger_penalty = float(spec.get("danger_penalty", DANGER_PENALTY))
        self.step_size = float(spec.get("step_size", STEP_SIZE))
        self.noise = float(spec.get("motion_noise_std", MOTION_NOISE_STD))
        self.max_macro_len = int(spec.get("max_macro_len", MAX_MACRO_LEN))
        self.horizon = int(spec.get("horizon", HORIZON))
        self._danger_r2 = [(x, y, r * r) for x, y, r in self.dangers]
        self._goal_r2 = [(x, y, r * r) for x, y, r in self.goals]
        self._land_r2 = [(x, y, r * r) for x, y, r in self.landmarks]

    # ------------------------------------------------------------------ geometry
    def free(self, x: float, y: float) -> bool:
        if x < 0.0 or y < 0.0 or x >= self.width or y >= self.height:
            return False
        return not self.blocked[int(y) * self.width + int(x)]

    def move(self, x: float, y: float, dx: float, dy: float) -> Point:
        """Displacement that conforms to the walls (slide along, never through)."""
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

    # ---------------------------------------------------------------- dynamics
    def step(self, x: float, y: float, heading: float, ex: float, ey: float):
        """One primitive step with externally drawn noise (ex, ey).

        Returns (x', y', reward, event, observation)."""
        v = self.step_size
        nx, ny = self.move(x, y, v * math.cos(heading) + ex, v * math.sin(heading) + ey)
        ev = self.event(nx, ny)
        if ev == DANGER:
            return nx, ny, self.danger_penalty, ev, None
        if ev == GOAL:
            return nx, ny, self.goal_reward, ev, None
        obs = (round(nx, 3), round(ny, 3)) if self.at_landmark(nx, ny) else None
        return nx, ny, self.step_penalty, ev, obs

    def macro(self, x: float, y: float, headings: Sequence[float], rng: random.Random):
        """Generative model G(s, a) for a macro action.

        Returns (x', y', discounted macro reward, event, last landmark
        observation or None, executed primitive steps)."""
        gamma = self.gamma
        sigma = self.noise
        gauss = rng.gauss
        v = self.step_size
        disc = 1.0
        total = 0.0
        last_obs = None
        n = 0
        for heading in headings:
            n += 1
            nx, ny = self.move(x, y, v * math.cos(heading) + gauss(0.0, sigma), v * math.sin(heading) + gauss(0.0, sigma))
            x, y = nx, ny
            ev = self.event(x, y)
            if ev == DANGER:
                total += disc * self.danger_penalty
                return x, y, total, ev, last_obs, n
            if ev == GOAL:
                total += disc * self.goal_reward
                return x, y, total, ev, last_obs, n
            total += disc * self.step_penalty
            disc *= gamma
            if self.at_landmark(x, y):
                last_obs = (x, y)
        return x, y, total, NONE, last_obs, n

    def initial_particles(self, count: int, rng: random.Random) -> List[Point]:
        out = [self.starts[i % len(self.starts)] for i in range(count)]
        rng.shuffle(out)
        return out


# ---------------------------------------------------------------------- roadmap
_NEIGHBOURS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
               (1, 1, math.sqrt(2.0)), (1, -1, math.sqrt(2.0)), (-1, 1, math.sqrt(2.0)), (-1, -1, math.sqrt(2.0))]


class Roadmap:
    """Lattice roadmap over the collision-free cells (the paper's offline PRM).

    Cells closer than ``clearance`` to a danger zone are excluded, so roadmap
    paths avoid danger zones *for the particle they were planned from*.
    Executed from a wrongly localised position the same open-loop path can
    still run into walls or danger zones; that is what makes the sampler a
    useful but insufficient heuristic.
    """

    def __init__(self, maze: Maze, clearance: float = 0.7, goal_probability: float = 0.5):
        self.maze = maze
        self.goal_probability = goal_probability
        w, h = maze.width, maze.height
        self.w, self.h = w, h
        ok = [False] * (w * h)
        for y in range(h):
            for x in range(w):
                idx = y * w + x
                if maze.blocked[idx]:
                    continue
                cx, cy = x + 0.5, y + 0.5
                safe = True
                for dx_, dy_, r in maze.dangers:
                    if math.hypot(cx - dx_, cy - dy_) < r + clearance:
                        safe = False
                        break
                ok[idx] = safe
        self.ok = ok
        self.snap = self._snap_table()
        self.targets: List[Tuple[str, float, float, float]] = (
            [("landmark", x, y, r) for x, y, r in maze.landmarks] + [("goal", x, y, r) for x, y, r in maze.goals]
        )
        self.fields = [self._field([(x, y, r)]) for _, x, y, r in self.targets]
        self.goal_field = self._field(list(maze.goals))
        self.landmark_ids = [i for i, t in enumerate(self.targets) if t[0] == "landmark"]
        self.goal_ids = [i for i, t in enumerate(self.targets) if t[0] == "goal"]

    def cell(self, x: float, y: float) -> int:
        xi = min(self.w - 1, max(0, int(x)))
        yi = min(self.h - 1, max(0, int(y)))
        return self.snap[yi * self.w + xi]

    def _snap_table(self) -> List[int]:
        """Nearest roadmap cell for every grid cell (multi-source BFS)."""
        w, h = self.w, self.h
        snap = [-1] * (w * h)
        frontier = []
        for idx, good in enumerate(self.ok):
            if good:
                snap[idx] = idx
                frontier.append(idx)
        while frontier:
            nxt = []
            for idx in frontier:
                x, y = idx % w, idx // w
                for dx, dy, _ in _NEIGHBOURS:
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h:
                        j = yy * w + xx
                        if snap[j] < 0:
                            snap[j] = snap[idx]
                            nxt.append(j)
            frontier = nxt
        return [s if s >= 0 else 0 for s in snap]

    def _field(self, regions: Sequence[Tuple[float, float, float]]):
        """Dijkstra distance (in steps) to a set of disc regions, plus a
        two-hop look-ahead waypoint for path following."""
        w, h, ok = self.w, self.h, self.ok
        inf = float("inf")
        dist = [inf] * (w * h)
        heap = []
        for gx, gy, r in regions:
            for y in range(h):
                for x in range(w):
                    idx = y * w + x
                    if ok[idx] and math.hypot(x + 0.5 - gx, y + 0.5 - gy) <= r + 0.25:
                        if dist[idx] > 0.0:
                            dist[idx] = 0.0
                            heapq.heappush(heap, (0.0, idx))
        while heap:
            d, idx = heapq.heappop(heap)
            if d > dist[idx]:
                continue
            x, y = idx % w, idx // w
            for dx, dy, cost in _NEIGHBOURS:
                xx, yy = x + dx, y + dy
                if not (0 <= xx < w and 0 <= yy < h):
                    continue
                j = yy * w + xx
                if not ok[j]:
                    continue
                if dx and dy and not (ok[y * w + xx] and ok[yy * w + x]):
                    continue  # no corner cutting
                nd = d + cost
                if nd < dist[j]:
                    dist[j] = nd
                    heapq.heappush(heap, (nd, j))
        nxt = list(range(w * h))
        for idx in range(w * h):
            if not ok[idx] or dist[idx] == inf or dist[idx] == 0.0:
                continue
            x, y = idx % w, idx // w
            best, best_d = idx, dist[idx]
            for dx, dy, cost in _NEIGHBOURS:
                xx, yy = x + dx, y + dy
                if not (0 <= xx < w and 0 <= yy < h):
                    continue
                j = yy * w + xx
                if not ok[j] or (dx and dy and not (ok[y * w + xx] and ok[yy * w + x])):
                    continue
                if dist[j] + cost < best_d - 1e-9 or (dist[j] < dist[best] and abs(dist[j] + cost - best_d) < 1e-9):
                    best, best_d = j, dist[j] + cost
            nxt[idx] = best
        look = [nxt[nxt[i]] for i in range(w * h)]
        centres = [((i % w) + 0.5, (i // w) + 0.5) for i in range(w * h)]
        way = [centres[look[i]] for i in range(w * h)]
        return dist, way

    # ---------------------------------------------------------------- queries
    def goal_steps(self, x: float, y: float) -> float:
        d = self.goal_field[0][self.cell(x, y)]
        return d if d != float("inf") else 2.0 * (self.w + self.h)

    def value_estimate(self, x: float, y: float) -> float:
        """Optimistic value of reaching the nearest goal along the roadmap."""
        m = self.maze
        d = self.goal_steps(x, y)
        gd = m.gamma ** d
        return m.step_penalty * (1.0 - gd) / (1.0 - m.gamma) + gd * m.goal_reward

    def path_headings(self, x: float, y: float, target: int, length: int) -> Tuple[float, ...]:
        """Open-loop macro tracing the roadmap path from (x, y) to a target."""
        m = self.maze
        _, tx, ty, tr = self.targets[target]
        dist, way = self.fields[target]
        tr2 = tr * tr
        out = []
        for _ in range(length):
            if (x - tx) * (x - tx) + (y - ty) * (y - ty) <= tr2:
                break
            c = self.cell(x, y)
            if dist[c] <= 1.0:
                wx, wy = tx, ty
            else:
                wx, wy = way[c]
            heading = math.atan2(wy - y, wx - x)
            out.append(round(heading, 4))
            x, y = m.move(x, y, m.step_size * math.cos(heading), m.step_size * math.sin(heading))
        if not out:
            out.append(round(math.atan2(ty - y, tx - x), 4))
        return tuple(out)

    def sample_target(self, rng: random.Random) -> int:
        if rng.random() < self.goal_probability:
            return rng.choice(self.goal_ids)
        return rng.choice(self.landmark_ids)

    def sample_key(self, x: float, y: float, rng: random.Random):
        """First half of ``sample_candidate``: the sampled target and the
        candidate key (target, start cell), without building the path."""
        target = self.sample_target(rng)
        return (target, self.cell(x, y)), target

    def sample_candidate(self, x: float, y: float, rng: random.Random, length: Optional[int] = None):
        """The paper's heuristic action sampler: pick a random landmark or goal
        region and return the truncated roadmap path from the particle.

        Returns (key, headings); the key identifies (target, start cell)."""
        target = self.sample_target(rng)
        length = length or self.maze.max_macro_len
        return (target, self.cell(x, y)), self.path_headings(x, y, target, length)


# ----------------------------------------------------------------- belief update
def update_particles(
    maze: Maze,
    particles: Sequence[Point],
    headings: Sequence[float],
    observations: Sequence[Observation],
    count: int,
    rng: random.Random,
) -> List[Point]:
    """Rejection-sampling belief update after executing ``headings`` and
    receiving the per-step ``observations`` (None or the true position).

    A landmark observation reveals the true position, so the belief collapses
    there and is propagated through the remaining steps.  Without one, sampled
    particles are propagated and kept only if they produce the same
    (non-)observations and do not terminate."""
    obs = list(observations)
    executed = len(obs)
    last = max((i for i, o in enumerate(obs) if o is not None), default=-1)
    if last >= 0:
        start = [(float(obs[last][0]), float(obs[last][1]))]
        first = last + 1
    else:
        start = list(particles)
        first = 0
    sigma = maze.noise
    v = maze.step_size
    accepted: List[Point] = []
    fallback: List[Point] = []
    attempts = 0
    limit = 30 * count
    while len(accepted) < count and attempts < limit:
        attempts += 1
        x, y = start[rng.randrange(len(start))]
        good = True
        for i in range(first, executed):
            hd = headings[i]
            x, y = maze.move(x, y, v * math.cos(hd) + rng.gauss(0.0, sigma), v * math.sin(hd) + rng.gauss(0.0, sigma))
            if maze.event(x, y) != NONE or maze.at_landmark(x, y) != (obs[i] is not None):
                good = False
                break
        if good:
            accepted.append((x, y))
        elif len(fallback) < count:
            fallback.append((x, y))
    if not accepted:
        accepted = fallback or list(start)
    while len(accepted) < count:
        accepted.append(accepted[rng.randrange(len(accepted))])
    return accepted


# ---------------------------------------------------------------- instances
def _carve(grid: List[List[str]], x0: int, y0: int, x1: int, y1: int, ch: str) -> None:
    for y in range(max(0, y0), min(len(grid), y1 + 1)):
        for x in range(max(0, x0), min(len(grid[0]), x1 + 1)):
            grid[y][x] = ch


def _connected(roadmap: Roadmap, start: Point, field_index: Optional[int] = None) -> bool:
    if field_index is None:
        return roadmap.goal_field[0][roadmap.cell(*start)] < float("inf")
    return roadmap.fields[field_index][0][roadmap.cell(*start)] < float("inf")


def _noise_free_rollout(maze: Maze, roadmap: Roadmap, plan_from: Point, run_from: Point, steps: int = 150) -> int:
    """Execute (noise-free) the roadmap path planned from one start but run
    from the other start.  Returns the terminal event (or NONE)."""
    goal_target = min(roadmap.goal_ids, key=lambda t: roadmap.fields[t][0][roadmap.cell(*plan_from)])
    px, py = plan_from
    headings: List[float] = []
    while len(headings) < steps:
        chunk = roadmap.path_headings(px, py, goal_target, maze.max_macro_len)
        for hd in chunk:
            px, py = maze.move(px, py, math.cos(hd), math.sin(hd))
        headings.extend(chunk)
        if maze.event(px, py) == GOAL:
            break
    x, y = run_from
    for hd in headings:
        x, y = maze.move(x, y, math.cos(hd), math.sin(hd))
        ev = maze.event(x, y)
        if ev != NONE:
            return ev
    return NONE


def generate_instance(seed: int, instance_id: Optional[str] = None) -> dict:
    """Procedurally generate one localisation-critical maze layout.

    Layout: closed WIDTH x HEIGHT maze; two candidate starts on the west side;
    two goal regions on the east side; a field of danger zones with narrow
    gaps between them; a few landmarks; random interior wall segments.  A
    layout is accepted only if both starts can reach a goal and a landmark on
    the roadmap and the route planned from one start runs into a danger zone
    when executed from the other (acting on a wrong belief is costly)."""
    rng = random.Random(seed)
    w, h = WIDTH, HEIGHT
    for _attempt in range(1000):
        grid = [["." for _ in range(w)] for _ in range(h)]
        _carve(grid, 0, 0, w - 1, 0, "#")
        _carve(grid, 0, h - 1, w - 1, h - 1, "#")
        _carve(grid, 0, 0, 0, h - 1, "#")
        _carve(grid, w - 1, 0, w - 1, h - 1, "#")
        lo_y = rng.uniform(3.0, h * 0.35)
        hi_y = rng.uniform(h * 0.65, h - 3.0)
        starts = [(rng.uniform(2.0, 4.5), lo_y), (rng.uniform(2.0, 4.5), hi_y)]
        goals = [
            (rng.uniform(w - 5.0, w - 2.5), rng.uniform(3.0, h * 0.45), 1.2),
            (rng.uniform(w - 5.0, w - 2.5), rng.uniform(h * 0.55, h - 3.0), 1.2),
        ]
        landmarks = []
        while len(landmarks) < N_LANDMARKS:
            p = (rng.uniform(7.0, w - 8.0), rng.uniform(2.5, h - 2.5), 1.3)
            if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 6.0 for q in landmarks):
                landmarks.append(p)
        keep = [(s[0], s[1], 1.5) for s in starts] + list(goals) + list(landmarks)
        dangers = []
        n_danger = rng.randint(*N_DANGERS)
        tries = 0
        while len(dangers) < n_danger and tries < 2000:
            tries += 1
            r = rng.uniform(*DANGER_RADIUS)
            p = (rng.uniform(7.0, w - 6.0), rng.uniform(1.5, h - 1.5), r)
            if all(math.hypot(p[0] - q[0], p[1] - q[1]) > r + q[2] + 1.0 for q in keep) and all(
                math.hypot(p[0] - q[0], p[1] - q[1]) > r + q[2] + DANGER_GAP for q in dangers
            ):
                dangers.append(p)
        for _ in range(rng.randint(*N_WALLS)):
            length = rng.randint(3, 8)
            if rng.random() < 0.6:
                x0 = rng.randint(6, w - 7)
                y0 = rng.randint(1, h - 2 - length)
                cells = [(x0, y0 + k) for k in range(length)]
            else:
                x0 = rng.randint(6, w - 7 - length)
                y0 = rng.randint(2, h - 3)
                cells = [(x0 + k, y0) for k in range(length)]
            if all(all(math.hypot(cx + 0.5 - q[0], cy + 0.5 - q[1]) > q[2] + 1.2 for q in keep) for cx, cy in cells):
                for cx, cy in cells:
                    grid[cy][cx] = "#"
        spec = {
            "grid": ["".join(row) for row in grid],
            "starts": [[round(s[0], 3), round(s[1], 3)] for s in starts],
            "goals": [[round(g[0], 3), round(g[1], 3), g[2]] for g in goals],
            "dangers": [[round(d[0], 3), round(d[1], 3), round(d[2], 3)] for d in dangers],
            "landmarks": [[round(m[0], 3), round(m[1], 3), m[2]] for m in landmarks],
        }
        spec.update(default_parameters())
        maze = Maze(spec)
        roadmap = Roadmap(maze)
        if not all(_connected(roadmap, s) for s in maze.starts):
            continue
        if not all(any(_connected(roadmap, s, t) for t in roadmap.landmark_ids) for s in maze.starts):
            continue
        risky = (
            _noise_free_rollout(maze, roadmap, maze.starts[0], maze.starts[1]) == DANGER
            or _noise_free_rollout(maze, roadmap, maze.starts[1], maze.starts[0]) == DANGER
        )
        if not risky:
            continue
        spec["id"] = instance_id or f"maze-{seed}"
        return spec
    raise RuntimeError(f"could not generate a valid instance for seed {seed}")
