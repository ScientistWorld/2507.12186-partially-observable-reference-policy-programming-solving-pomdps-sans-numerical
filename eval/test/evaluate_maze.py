"""Held-out test-slice scoring for scaled maze episode artifacts.

This evaluator is intentionally standalone from eval/train. It reads the same
method-produced JSONL artifact format, selects the complementary episode split,
and writes held-out scores for the method keys selected by the train slice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List, Optional


SLICE = "test"
SPLIT_SALT = "researchgym_porpp_scaled_maze_v2"
BASELINE_METHODS = {"refpol", "pomcp"}
EXCLUDED_EPISODE_SUFFIXES = ("_low_episodes", "_high_episodes")
REQUIRED_EPISODE_FIELDS = {"seed", "method", "success", "total_reward", "steps", "trace"}
SUCCESS_MARGIN_SCALE = 0.2
REWARD_MARGIN_SCALE = 500.0


def is_finite_number(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def is_valid_episode(row: dict) -> bool:
    if not isinstance(row, dict) or not REQUIRED_EPISODE_FIELDS.issubset(row):
        return False
    return (
        isinstance(row["seed"], int)
        and isinstance(row["method"], str)
        and isinstance(row["success"], bool)
        and is_finite_number(row["total_reward"])
        and isinstance(row["steps"], int)
        and row["steps"] >= 0
        and isinstance(row["trace"], list)
    )


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    row = {}
                row["_valid_episode"] = is_valid_episode(row)
                rows.append(row)
    return rows


def episode_sort_key(row: dict) -> tuple:
    return (row.get("seed", 0), row.get("method", ""), row.get("total_reward", 0.0))


def split_bit(row: dict) -> int:
    seed = row.get("seed", "")
    digest = hashlib.sha256(f"{SPLIT_SALT}:{seed}".encode("utf-8")).digest()
    return digest[0] & 1


def test_partition(rows: List[dict]) -> List[dict]:
    selected = [row for row in rows if split_bit(row) == 1]
    if selected or not rows:
        return selected
    ordered = sorted(rows, key=episode_sort_key)
    return [row for idx, row in enumerate(ordered) if idx % 2 == 1]


def summarize(rows: List[dict]) -> dict:
    valid_rows = [row for row in rows if row.get("_valid_episode")]
    if not rows:
        return {
            "episodes": 0,
            "valid_episode_rate": 0.0,
            "unique_seed_rate": 0.0,
            "success_rate": 0.0,
            "mean_total_reward": 0.0,
            "stderr_total_reward": 0.0,
        }
    if not valid_rows:
        return {
            "episodes": 0,
            "valid_episode_rate": 0.0,
            "unique_seed_rate": 0.0,
            "success_rate": 0.0,
            "mean_total_reward": 0.0,
            "stderr_total_reward": 0.0,
        }
    rewards = [float(r["total_reward"]) for r in valid_rows]
    seeds = [r["seed"] for r in valid_rows]
    return {
        "episodes": len(valid_rows),
        "valid_episode_rate": len(valid_rows) / len(rows),
        "unique_seed_rate": len(set(seeds)) / len(seeds),
        "success_rate": sum(1.0 for r in valid_rows if r.get("success")) / len(valid_rows),
        "mean_total_reward": mean(rewards),
        "stderr_total_reward": (stdev(rewards) / math.sqrt(len(rewards))) if len(rewards) > 1 else 0.0,
    }


def beats_all_on_success_and_reward(candidate: dict, baselines: Iterable[dict]) -> float:
    usable = [b for b in baselines if b.get("episodes", 0)]
    if not candidate.get("episodes", 0) or not usable:
        return 0.0
    for baseline in usable:
        if candidate["success_rate"] <= baseline["success_rate"]:
            return 0.0
        if candidate["mean_total_reward"] <= baseline["mean_total_reward"]:
            return 0.0
    return 1.0


def core_claim_margin_score(candidate: dict, baselines: Iterable[dict]) -> float:
    usable = [b for b in baselines if b.get("episodes", 0)]
    if not candidate.get("episodes", 0) or not usable:
        return 0.0
    success_margin = candidate["success_rate"] - max(b["success_rate"] for b in usable)
    reward_margin = candidate["mean_total_reward"] - max(b["mean_total_reward"] for b in usable)
    if success_margin <= 0.0 or reward_margin <= 0.0:
        return 0.0
    normalized = min(success_margin / SUCCESS_MARGIN_SCALE, reward_margin / REWARD_MARGIN_SCALE)
    return max(0.0, min(1.0, normalized))


def method_name_from_path(path: Path) -> str:
    stem = path.stem
    if stem.endswith("_episodes"):
        return stem[: -len("_episodes")]
    return stem


def discover_episode_paths(checkpoints_dir: Path) -> Dict[str, Path]:
    paths: Dict[str, Path] = {}
    for path in sorted(checkpoints_dir.glob("*_episodes.jsonl")):
        stem = path.stem
        if any(stem.endswith(suffix) for suffix in EXCLUDED_EPISODE_SUFFIXES):
            continue
        paths[method_name_from_path(path)] = path
    return paths


def add_named_path(paths: Dict[str, Path], name: str, path: Path) -> None:
    if path.exists():
        paths[name] = path


def train_method_names(path: Path) -> Optional[List[str]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        scores = json.load(f)
    results = scores.get("scaled_maze_online_planning", {}).get("results", {})
    return sorted(results)


def build_scores(paths: Dict[str, Path], method_names: Optional[List[str]]) -> dict:
    selected_names = method_names if method_names is not None else sorted(paths)
    summaries = {
        name: summarize(test_partition(read_jsonl(paths[name]))) if name in paths else summarize([])
        for name in selected_names
    }
    refpol = summaries.get("refpol", summarize([]))
    for name, summary in summaries.items():
        if summary.get("episodes", 0) and refpol.get("episodes", 0):
            summary["success_gap_vs_refpol"] = summary["success_rate"] - refpol["success_rate"]
            summary["reward_gap_vs_refpol"] = summary["mean_total_reward"] - refpol["mean_total_reward"]
        else:
            summary["success_gap_vs_refpol"] = 0.0
            summary["reward_gap_vs_refpol"] = 0.0

    baseline_summaries = [summaries[name] for name in sorted(BASELINE_METHODS) if name in summaries]
    for name, summary in summaries.items():
        if name in BASELINE_METHODS:
            summary["core_claim_supported"] = 0.0
            summary["core_claim_margin_score"] = 0.0
        else:
            summary["core_claim_supported"] = beats_all_on_success_and_reward(summary, baseline_summaries)
            summary["core_claim_margin_score"] = core_claim_margin_score(summary, baseline_summaries)

    return {"scaled_maze_online_planning": {"results": summaries}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoints_dir", nargs="?", type=Path, default=Path("checkpoints"))
    parser.add_argument("--porpp", type=Path)
    parser.add_argument("--refpol", type=Path)
    parser.add_argument("--pomcp", type=Path)
    parser.add_argument("--porpp-low", type=Path)
    parser.add_argument("--porpp-high", type=Path)
    parser.add_argument("--include-anytime", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("scoring/scores_test.json"))
    args = parser.parse_args()

    checkpoints_dir = args.checkpoints_dir
    paths = discover_episode_paths(checkpoints_dir)
    add_named_path(paths, "porpp", args.porpp or checkpoints_dir / "porpp_episodes.jsonl")
    add_named_path(paths, "refpol", args.refpol or checkpoints_dir / "refpol_episodes.jsonl")
    add_named_path(paths, "pomcp", args.pomcp or checkpoints_dir / "pomcp_episodes.jsonl")

    scores = build_scores(paths, train_method_names(Path("scoring/scores_train.json")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"slice": SLICE, "scores": scores}, indent=2))


if __name__ == "__main__":
    main()
