"""Evaluate episode artifacts for the PORPP benchmark."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List


SUCCESS_MARGIN_SCALE = 0.2
REWARD_MARGIN_SCALE = 500.0


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def summarize(rows: List[dict]) -> dict:
    if not rows:
        return {"episodes": 0, "success_rate": 0.0, "mean_total_reward": 0.0, "stderr_total_reward": 0.0}
    rewards = [float(r["total_reward"]) for r in rows]
    return {
        "episodes": len(rows),
        "success_rate": sum(1.0 for r in rows if r.get("success")) / len(rows),
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--porpp", type=Path, default=Path("checkpoints/porpp_episodes.jsonl"))
    parser.add_argument("--refpol", type=Path, default=Path("checkpoints/refpol_episodes.jsonl"))
    parser.add_argument("--pomcp", type=Path, default=Path("checkpoints/pomcp_episodes.jsonl"))
    parser.add_argument("--porpp-low", type=Path, default=Path("checkpoints/porpp_low_episodes.jsonl"))
    parser.add_argument("--porpp-high", type=Path, default=Path("checkpoints/porpp_high_episodes.jsonl"))
    parser.add_argument("--include-anytime", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("scoring/scores.json"))
    args = parser.parse_args()

    porpp_summary = summarize(read_jsonl(args.porpp))
    refpol_summary = summarize(read_jsonl(args.refpol))
    pomcp_summary = summarize(read_jsonl(args.pomcp))
    if porpp_summary["episodes"] and refpol_summary["episodes"]:
        porpp_summary["success_gap_vs_refpol"] = porpp_summary["success_rate"] - refpol_summary["success_rate"]
        porpp_summary["reward_gap_vs_refpol"] = porpp_summary["mean_total_reward"] - refpol_summary["mean_total_reward"]
        refpol_summary["success_gap_vs_refpol"] = 0.0
        refpol_summary["reward_gap_vs_refpol"] = 0.0
    else:
        porpp_summary["success_gap_vs_refpol"] = 0.0
        porpp_summary["reward_gap_vs_refpol"] = 0.0
        refpol_summary["success_gap_vs_refpol"] = 0.0
        refpol_summary["reward_gap_vs_refpol"] = 0.0
    if pomcp_summary["episodes"] and refpol_summary["episodes"]:
        pomcp_summary["success_gap_vs_refpol"] = pomcp_summary["success_rate"] - refpol_summary["success_rate"]
        pomcp_summary["reward_gap_vs_refpol"] = pomcp_summary["mean_total_reward"] - refpol_summary["mean_total_reward"]
    else:
        pomcp_summary["success_gap_vs_refpol"] = 0.0
        pomcp_summary["reward_gap_vs_refpol"] = 0.0
    porpp_summary["core_claim_supported"] = beats_all_on_success_and_reward(
        porpp_summary,
        [refpol_summary, pomcp_summary],
    )
    porpp_summary["core_claim_margin_score"] = core_claim_margin_score(
        porpp_summary,
        [refpol_summary, pomcp_summary],
    )
    refpol_summary["core_claim_margin_score"] = 0.0
    pomcp_summary["core_claim_margin_score"] = 0.0

    scores = {
        "scaled_maze_online_planning": {
            "results": {
                "porpp": porpp_summary,
                "refpol": refpol_summary,
            }
        }
    }
    if pomcp_summary["episodes"]:
        scores["scaled_maze_online_planning"]["results"]["pomcp"] = pomcp_summary
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
