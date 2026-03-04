"""
Rank-7 Elkies lightweight sweep — single worker, reduced params.

The Elkies family has coefficients O(10^11), making Euler products
extremely expensive. This uses minimal parameters to fit Jules' limits.

Usage:
    PYTHONPATH=. python jules_orders/jules_bsd_rank7_light.py
"""
import sys
import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.rank_estimator import RankEstimator

SEED = ("rank7_elkies", -94816050, 368541849450, 7)
PARAMS = {
    "radius": 30,
    "step": 10,
    "prime_bound": 2000,
    "precision": 25,
    "height_bound": 15,
    "output_dir": "evidence/phase3",
}


def main():
    label, base_a, base_b, seed_rank = SEED
    radius = PARAMS["radius"]
    step = PARAMS["step"]
    output_dir = Path(PARAMS["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print(f" BSD RANK-7 ELKIES — LIGHTWEIGHT SWEEP")
    print(f" prime_bound={PARAMS['prime_bound']}, dps={PARAMS['precision']}")
    print(f" radius={radius}, step={step} (single worker)")
    print("=" * 55)

    estimator = RankEstimator(
        prime_bound=PARAMS["prime_bound"],
        precision=PARAMS["precision"],
        height_bound=PARAMS["height_bound"],
    )

    candidates = []
    for da in range(-radius, radius + 1, step):
        for db in range(-radius, radius + 1, step):
            a = base_a + da
            b = base_b + db
            disc = -16 * (4 * a**3 + 27 * b**2)
            if disc != 0:
                candidates.append((a, b))

    print(f"  Candidates: {len(candidates)}")

    verdicts_path = output_dir / f"verdicts_{label}.jsonl"
    telemetry_path = output_dir / f"telemetry_{label}.jsonl"

    n_evaluated = 0
    n_consistent = 0
    n_anomaly = 0
    n_inconclusive = 0
    n_errors = 0
    start_time = time.time()

    with open(verdicts_path, "w", encoding="utf-8") as vf, \
         open(telemetry_path, "w", encoding="utf-8") as tf:

        tf.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "START", "n_candidates": len(candidates),
        }) + "\n")

        for i, (a, b) in enumerate(candidates):
            try:
                verdict = estimator.analyze(a, b)
                line = {
                    "curve_a": a, "curve_b": b,
                    "seed_label": label, "seed_rank": seed_rank,
                    "algebraic_rank_lower": verdict.algebraic.lower,
                    "algebraic_rank_upper": verdict.algebraic.upper,
                    "analytic_rank": verdict.analytic_rank,
                    "L_at_1": verdict.L_values.get(0, None),
                    "verdict": verdict.verdict,
                    "confidence": verdict.confidence,
                }
                vf.write(json.dumps(line) + "\n")
                vf.flush()

                if verdict.verdict == "CONSISTENT":
                    n_consistent += 1
                elif verdict.verdict == "ANOMALY":
                    n_anomaly += 1
                    print(f"  ⚠️ ANOMALY at E({a},{b})")
                else:
                    n_inconclusive += 1

                n_evaluated += 1

            except Exception as e:
                n_errors += 1
                n_evaluated += 1

            if n_evaluated % 10 == 0:
                elapsed = time.time() - start_time
                rate = n_evaluated / elapsed if elapsed > 0 else 0
                print(f"  [{n_evaluated}/{len(candidates)}] {rate:.3f}/s | "
                      f"C={n_consistent} A={n_anomaly} I={n_inconclusive} E={n_errors}",
                      flush=True)
                tf.write(json.dumps({
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "event": f"PROGRESS_{n_evaluated}",
                    "rate": round(rate, 3),
                }) + "\n")
                tf.flush()

    elapsed = time.time() - start_time

    manifest = {
        "seed_label": label, "seed_rank": seed_rank, "phase": 3,
        "n_workers": 1, "prime_bound": PARAMS["prime_bound"],
        "precision": PARAMS["precision"],
        "radius": radius, "step": step,
        "n_curves_evaluated": n_evaluated,
        "n_consistent": n_consistent, "n_anomaly": n_anomaly,
        "n_inconclusive": n_inconclusive, "n_errors": n_errors,
        "wall_time_s": round(elapsed, 2),
        "rate": round(n_evaluated / elapsed, 3) if elapsed > 0 else 0,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "fingerprint": hashlib.sha256(f"BSD_P3_{label}_light".encode()).hexdigest(),
    }

    manifest_path = output_dir / f"manifest_{label}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n{'=' * 55}")
    print(f"  RANK-7 ELKIES COMPLETE")
    print(f"  Curves: {n_evaluated} | Anomalies: {n_anomaly}")
    print(f"  Time: {elapsed:.1f}s | Rate: {n_evaluated/elapsed:.3f}/s")
    print(f"  BSD: {'CONSISTENT ✅' if n_anomaly == 0 else 'ANOMALY ⚠️'}")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
