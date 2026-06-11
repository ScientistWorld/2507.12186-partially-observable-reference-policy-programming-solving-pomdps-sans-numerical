"""Evaluate episode artifacts for the scaled maze benchmark.

This evaluator is method-agnostic: methods write episode JSONL artifacts under
checkpoints/, and the evaluator scores whatever method artifacts are present.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List


REQUIRED_EPISODE_FIELDS = {"seed", "method", "success", "total_reward", "steps", "trace"}
BASELINE_METHODS = {"refpol", "pomcp"}
EXCLUDED_EPISODE_SUFFIXES = ("_low_episodes", "_high_episodes")
SCENARIO_EXPERIMENTS = {
    "default": "scaled_maze_online_planning",
    "scaled_maze": "scaled_maze_online_planning",
    "mirrored_danger": "scaled_maze_mirrored_danger_planning",
}
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
    """Return 1.0 when the candidate strictly beats every available baseline."""
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
    """Normalized success-and-reward margin over the strongest available baseline."""
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


def discover_episode_paths(checkpoints_dir: Path) -> Dict[str, List[Path]]:
    paths: Dict[str, List[Path]] = {}
    for path in sorted(checkpoints_dir.rglob("*_episodes.jsonl")):
        stem = path.stem
        if any(stem.endswith(suffix) for suffix in EXCLUDED_EPISODE_SUFFIXES):
            continue
        paths.setdefault(method_name_from_path(path), []).append(path)
    return paths


def add_named_path(paths: Dict[str, List[Path]], name: str, path: Path | None) -> None:
    if path is not None and path.exists():
        current = paths.setdefault(name, [])
        if path not in current:
            current.append(path)


def scenario_from_row(row: dict, path: Path) -> str:
    scenario = row.get("scenario")
    if isinstance(scenario, str) and scenario:
        return scenario
    if "mirrored_danger" in path.parts:
        return "mirrored_danger"
    return "default"


def build_one_experiment(method_rows: Dict[str, List[dict]]) -> dict:
    summaries = {
        name: summarize(rows)
        for name, rows in sorted(method_rows.items())
    }
    refpol = summaries.get("refpol", summarize([]))
    for summary in summaries.values():
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
    return {"results": summaries}


def build_scores(paths: Dict[str, List[Path]]) -> dict:
    grouped: Dict[str, Dict[str, List[dict]]] = {}
    for name, path_list in sorted(paths.items()):
        for path in path_list:
            for row in read_jsonl(path):
                scenario = scenario_from_row(row, path)
                grouped.setdefault(scenario, {}).setdefault(name, []).append(row)

    scores = {}
    for scenario, method_rows in sorted(grouped.items()):
        exp_name = SCENARIO_EXPERIMENTS.get(scenario, f"scaled_maze_{scenario}_planning")
        scores[exp_name] = build_one_experiment(method_rows)
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoints_dir", nargs="?", type=Path, default=Path("checkpoints"))
    parser.add_argument("--porpp", type=Path)
    parser.add_argument("--refpol", type=Path)
    parser.add_argument("--pomcp", type=Path)
    parser.add_argument("--porpp-low", type=Path, default=Path("checkpoints/porpp_low_episodes.jsonl"))
    parser.add_argument("--porpp-high", type=Path, default=Path("checkpoints/porpp_high_episodes.jsonl"))
    parser.add_argument("--include-anytime", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("scoring/scores.json"))
    args = parser.parse_args()

    paths = discover_episode_paths(args.checkpoints_dir)
    add_named_path(paths, "porpp", args.porpp or args.checkpoints_dir / "porpp_episodes.jsonl")
    add_named_path(paths, "refpol", args.refpol or args.checkpoints_dir / "refpol_episodes.jsonl")
    add_named_path(paths, "pomcp", args.pomcp or args.checkpoints_dir / "pomcp_episodes.jsonl")

    scores = build_scores(paths)
    low_rows = read_jsonl(args.porpp_low)
    high_rows = read_jsonl(args.porpp_high)
    if args.include_anytime and low_rows and high_rows:
        low_summary = summarize(low_rows)
        high_summary = summarize(high_rows)
        low_summary["success_gap_vs_low_budget"] = 0.0
        low_summary["reward_gap_vs_low_budget"] = 0.0
        high_summary["success_gap_vs_low_budget"] = high_summary["success_rate"] - low_summary["success_rate"]
        high_summary["reward_gap_vs_low_budget"] = high_summary["mean_total_reward"] - low_summary["mean_total_reward"]
        scores["scaled_maze_anytime_planning"] = {
            "results": {
                "porpp_low_budget": low_summary,
                "porpp_high_budget": high_summary,
            }
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
