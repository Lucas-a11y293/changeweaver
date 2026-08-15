"""Small reproducible benchmark for the local fixture or a supplied repository."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from changeweaver.application.services import build_snapshot
from changeweaver.infrastructure.config import load_contract


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("tests/fixtures/sample_app"))
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()
    if args.iterations < 1:
        raise SystemExit("--iterations must be greater than zero")
    root = args.root.resolve(strict=True)
    contract = load_contract(root)
    durations: list[float] = []
    snapshot = None
    for _ in range(args.iterations):
        started = time.perf_counter()
        snapshot = build_snapshot(root, contract)
        durations.append(time.perf_counter() - started)
    assert snapshot is not None
    print(
        json.dumps(
            {
                "root": str(root),
                "iterations": args.iterations,
                "min_seconds": min(durations),
                "max_seconds": max(durations),
                "mean_seconds": sum(durations) / len(durations),
                "nodes": len(snapshot.nodes),
                "edges": len(snapshot.edges),
                "digest": snapshot.digest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
