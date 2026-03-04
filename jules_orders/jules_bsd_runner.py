"""
Jules BSD Runner -- Block-based execution adapter for Jules distributed lab.

Executes a single block of the BSD falsifiability campaign.
Designed to be invoked by Jules with block parameters.

Usage:
    python jules_orders/jules_bsd_runner.py --block-id 0 --seed rank0_control \
        --radius 100 --side left --prime-bound 5000 --precision 30

Output:
    evidence/phase1/verdicts_block_{id}.jsonl
    evidence/phase1/manifest_block_{id}.json
    evidence/phase1/telemetry_block_{id}.jsonl
"""
import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.elliptic_curve import EllipticCurve
from src.candidate_generator import HIGH_RANK_SEEDS, generate_neighborhood
from src.rank_estimator import RankEstimator


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class Telemetry:
    """Append-only telemetry logger for Jules block execution."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **kwargs):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            **kwargs,
        }
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Block runner
# ---------------------------------------------------------------------------

def get_seed_by_label(label: str):
    for seed in HIGH_RANK_SEEDS:
        if seed[0] == label:
            return seed
    raise ValueError(f"Unknown seed label: {label}")


def run_block(
    block_id: int,
    seed_label: str,
    radius: int,
    side: str,  # "left" (negative offsets) or "right" (positive offsets)
    prime_bound: int,
    precision: int,
    height_bound: int,
    output_dir: Path,
):
    """Execute a single block of the BSD falsifiability sweep."""
    print(f"{'='*60}")
    print(f"JULES BSD BLOCK {block_id} — {seed_label} ({side})")
    print(f"prime_bound={prime_bound}, precision={precision}")
    print(f"{'='*60}")

    # Resolve seed
    seed = get_seed_by_label(seed_label)
    _, base_a, base_b, seed_rank = seed

    # Output paths
    output_dir.mkdir(parents=True, exist_ok=True)
    verdicts_path = output_dir / f"verdicts_block_{block_id}.jsonl"
    manifest_path = output_dir / f"manifest_block_{block_id}.json"
    telemetry_path = output_dir / f"telemetry_block_{block_id}.jsonl"

    tel = Telemetry(telemetry_path)
    tel.emit("BLOCK_START", block_id=block_id, seed=seed_label, side=side)

    # Create estimator
    estimator = RankEstimator(
        prime_bound=prime_bound,
        precision=precision,
        height_bound=height_bound,
    )

    # Generate candidates for this half
    if side == "left":
        da_range = range(-radius, 1)
    else:
        da_range = range(0, radius + 1)

    # Counters
    n_evaluated = 0
    n_consistent = 0
    n_anomaly = 0
    n_inconclusive = 0
    n_errors = 0
    start_time = time.time()

    with open(verdicts_path, "w", encoding="utf-8") as vf:
        for da in da_range:
            for db in range(-radius, radius + 1):
                a = base_a + da
                b = base_b + db
                disc = -16 * (4 * a**3 + 27 * b**2)
                if disc == 0:
                    continue

                try:
                    verdict = estimator.analyze(a, b)
                    line = {
                        "curve_a": a,
                        "curve_b": b,
                        "algebraic_rank_lower": verdict.algebraic.lower,
                        "algebraic_rank_upper": verdict.algebraic.upper,
                        "analytic_rank": verdict.analytic_rank,
                        "L_at_1": verdict.L_values.get(0, None),
                        "verdict": verdict.verdict,
                        "confidence": verdict.confidence,
                    }
                    vf.write(json.dumps(line) + "\n")

                    if verdict.verdict == "CONSISTENT":
                        n_consistent += 1
                    elif verdict.verdict == "ANOMALY":
                        n_anomaly += 1
                        tel.emit(
                            "ANOMALY_DETECTED",
                            curve_a=a, curve_b=b,
                            analytic_rank=verdict.analytic_rank,
                            algebraic_lower=verdict.algebraic.lower,
                            confidence=verdict.confidence,
                        )
                    else:
                        n_inconclusive += 1

                    n_evaluated += 1

                except Exception as e:
                    n_errors += 1
                    n_evaluated += 1

                # Progress every 500 curves
                if n_evaluated % 500 == 0 and n_evaluated > 0:
                    elapsed = time.time() - start_time
                    rate = n_evaluated / elapsed if elapsed > 0 else 0
                    tel.emit(
                        f"PROGRESS_{n_evaluated}",
                        evaluated=n_evaluated,
                        anomalies=n_anomaly,
                        rate_per_sec=round(rate, 2),
                    )
                    print(
                        f"  [{n_evaluated}] "
                        f"rate={rate:.1f}/s | "
                        f"anomalies={n_anomaly} | "
                        f"errors={n_errors}"
                    )

    elapsed = time.time() - start_time

    # Write manifest
    manifest = {
        "block_id": block_id,
        "probe": ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO",
                   "FOXTROT", "GOLF", "HOTEL", "INDIA", "JULIET"][block_id],
        "seed_label": seed_label,
        "seed_rank": seed_rank,
        "base_a": base_a,
        "base_b": base_b,
        "radius": radius,
        "side": side,
        "prime_bound": prime_bound,
        "precision": precision,
        "height_bound": height_bound,
        "n_curves_evaluated": n_evaluated,
        "n_consistent": n_consistent,
        "n_anomaly": n_anomaly,
        "n_inconclusive": n_inconclusive,
        "n_errors": n_errors,
        "wall_time_s": round(elapsed, 2),
        "rate_curves_per_sec": round(n_evaluated / elapsed, 2) if elapsed > 0 else 0,
        "status": "OK" if n_errors < n_evaluated * 0.1 else "PARTIAL",
        "completed_at": datetime.utcnow().isoformat() + "Z",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    tel.emit("BLOCK_DONE", **manifest)

    print(f"\n{'='*60}")
    print(f"BLOCK {block_id} COMPLETE")
    print(f"  Curves: {n_evaluated}")
    print(f"  Consistent: {n_consistent}")
    print(f"  Anomalies: {n_anomaly}")
    print(f"  Inconclusive: {n_inconclusive}")
    print(f"  Errors: {n_errors}")
    print(f"  Time: {elapsed:.1f}s ({n_evaluated/elapsed:.1f} curves/s)")
    print(f"{'='*60}")

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Jules BSD Block Runner — execute one block of the falsifiability sweep"
    )
    parser.add_argument("--block-id", type=int, required=True, help="Block index (0-9)")
    parser.add_argument("--seed", type=str, required=True, help="Seed label from HIGH_RANK_SEEDS")
    parser.add_argument("--radius", type=int, default=100, help="Neighborhood radius")
    parser.add_argument("--side", type=str, choices=["left", "right"], required=True)
    parser.add_argument("--prime-bound", type=int, default=5000)
    parser.add_argument("--precision", type=int, default=30)
    parser.add_argument("--height-bound", type=int, default=50)
    parser.add_argument("--output-dir", type=str, default="evidence/phase1")
    args = parser.parse_args()

    run_block(
        block_id=args.block_id,
        seed_label=args.seed,
        radius=args.radius,
        side=args.side,
        prime_bound=args.prime_bound,
        precision=args.precision,
        height_bound=args.height_bound,
        output_dir=Path(args.output_dir),
    )
