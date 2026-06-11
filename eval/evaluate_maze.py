"""Evaluate episode artifacts for the PORPP benchmark."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--porpp", type=Path, default=Path("checkpoints/porpp_episodes.jsonl"))
    parser.add_argument("--refpol", type=Path, default=Path("checkpoints/refpol_episodes.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("scoring/scores.json"))
    args = parser.parse_args()

    porpp_summary = summarize(read_jsonl(args.porpp))
    refpol_summary = summarize(read_jsonl(args.refpol))
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

    scores = {
        "scaled_maze_online_planning": {
            "results": {
                "porpp": porpp_summary,
                "refpol": refpol_summary,
            }
        }
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
