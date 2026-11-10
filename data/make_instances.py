"""Write a list of evaluation instances (public layout + evaluator-only fields).

Each record is a public maze spec from ``generate_instance`` plus two fields
that only the evaluator uses: ``env_seed`` (noise stream of the real
environment) and ``true_start`` (which of the two starts is the real one;
balanced across the list).

    python -m data.make_instances --out eval/train/instances.json --count 100 --base-seed 100000 --prefix train
    python -m data.make_instances --out <file> --count 200 --random-seeds --prefix test

``--random-seeds`` draws layout and noise seeds from the OS entropy pool and
does not record them, so such a list can only be reproduced from its file.
"""

from __future__ import annotations

import argparse
import json
import random
import secrets
from pathlib import Path

from data.maze2d import generate_instance


def build(count: int, prefix: str, base_seed: int, random_seeds: bool) -> list:
    picker = random.Random(None if random_seeds else base_seed + 7919)
    starts = [i % 2 for i in range(count)]
    picker.shuffle(starts)
    out = []
    for i in range(count):
        layout_seed = secrets.randbits(48) if random_seeds else base_seed + i
        spec = generate_instance(layout_seed, f"{prefix}-{i:03d}")
        spec["env_seed"] = secrets.randbits(31) if random_seeds else picker.randrange(2**31)
        spec["true_start"] = starts[i]
        out.append(spec)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--base-seed", type=int, default=0)
    parser.add_argument("--random-seeds", action="store_true")
    args = parser.parse_args()
    instances = build(args.count, args.prefix, args.base_seed, args.random_seeds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(instances, separators=(",", ":")) + "\n")
    print(f"wrote {len(instances)} instances to {args.out}")


if __name__ == "__main__":
    main()
