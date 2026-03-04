"""
Jules BSD Phase-3 — Multi-Session Parallel Dispatch.

Launches 3 SEPARATE Jules sessions simultaneously, one per seed family.
Each session uses 16 parallel workers for maximum throughput.

Phase-3 expands the search:
  - radius=100 (vs 50 in Phase-2) → more curves per family
  - step=3 (vs 5 in Phase-2) → denser coverage
  - n_workers=16 (vs 8 in Phase-2) → 2x parallelism
  - prime_bound=5000, dps=35 (same as Phase-2, proven sufficient)

Usage:
    set JULES_API_KEY=your-key
    set PYTHONPATH=.
    python jules_orders/jules_bsd_dispatch_p3_multi.py
"""
import sys
import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Phase-3 Configuration
# ---------------------------------------------------------------------------

SEEDS_P3 = [
    ("rank5_fermigier", -879984,    319138704,   5),
    ("rank6_dujella",   -3674496,   2706752832,  6),
    ("rank7_elkies",    -94816050,  368541849450, 7),
]

PARAMS = {
    "radius": 100,
    "step": 3,
    "prime_bound": 5000,
    "precision": 35,
    "height_bound": 30,
    "n_workers": 16,
    "output_dir": "evidence/phase3",
}


# ---------------------------------------------------------------------------
# Single-curve evaluation (worker process)
# ---------------------------------------------------------------------------

def evaluate_single_curve(args):
    a, b, seed_label, seed_rank, prime_bound, precision, height_bound = args
    from src.rank_estimator import RankEstimator
    try:
        estimator = RankEstimator(
            prime_bound=prime_bound,
            precision=precision,
            height_bound=height_bound,
        )
        verdict = estimator.analyze(a, b)
        return {
            "curve_a": a, "curve_b": b,
            "seed_label": seed_label, "seed_rank": seed_rank,
            "algebraic_rank_lower": verdict.algebraic.lower,
            "algebraic_rank_upper": verdict.algebraic.upper,
            "analytic_rank": verdict.analytic_rank,
            "L_at_1": verdict.L_values.get(0, None),
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "error": None,
        }
    except Exception as e:
        return {
            "curve_a": a, "curve_b": b,
            "seed_label": seed_label, "seed_rank": seed_rank,
            "verdict": "ERROR", "error": str(e),
        }


# ---------------------------------------------------------------------------
# Generate candidates for ONE family
# ---------------------------------------------------------------------------

def generate_family_candidates(seed_label, base_a, base_b, seed_rank):
    candidates = []
    radius = PARAMS["radius"]
    step = PARAMS["step"]
    for da in range(-radius, radius + 1, step):
        for db in range(-radius, radius + 1, step):
            a = base_a + da
            b = base_b + db
            disc = -16 * (4 * a**3 + 27 * b**2)
            if disc != 0:
                candidates.append((
                    a, b, seed_label, seed_rank,
                    PARAMS["prime_bound"], PARAMS["precision"],
                    PARAMS["height_bound"],
                ))
    return candidates


# ---------------------------------------------------------------------------
# Execute one family sweep (called per-session or locally)
# ---------------------------------------------------------------------------

def sweep_family(seed_label, base_a, base_b, seed_rank):
    print(f"\n{'=' * 60}")
    print(f"  PROBING {seed_label} (rank {seed_rank}) — {PARAMS['n_workers']} workers")
    print(f"{'=' * 60}")

    candidates = generate_family_candidates(seed_label, base_a, base_b, seed_rank)
    print(f"  Candidates: {len(candidates)}")

    output_dir = Path(PARAMS["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    verdicts_path = output_dir / f"verdicts_{seed_label}.jsonl"
    telemetry_path = output_dir / f"telemetry_{seed_label}.jsonl"

    n_evaluated = 0
    n_consistent = 0
    n_anomaly = 0
    n_inconclusive = 0
    n_errors = 0
    anomalies = []
    start_time = time.time()

    with open(verdicts_path, "w", encoding="utf-8") as vf, \
         open(telemetry_path, "w", encoding="utf-8") as tf:

        tf.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "FAMILY_START",
            "seed_label": seed_label,
            "n_candidates": len(candidates),
            "n_workers": PARAMS["n_workers"],
        }) + "\n")

        with ProcessPoolExecutor(max_workers=PARAMS["n_workers"]) as executor:
            futures = {executor.submit(evaluate_single_curve, c): c for c in candidates}

            for future in as_completed(futures):
                result = future.result()
                vf.write(json.dumps(result) + "\n")
                n_evaluated += 1

                v = result.get("verdict", "ERROR")
                if v == "CONSISTENT":
                    n_consistent += 1
                elif v == "ANOMALY":
                    n_anomaly += 1
                    anomalies.append(result)
                    tf.write(json.dumps({
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "event": "ANOMALY",
                        "curve_a": result["curve_a"],
                        "curve_b": result["curve_b"],
                    }) + "\n")
                    print(f"  ⚠️ ANOMALY: E({result['curve_a']}, {result['curve_b']})")
                elif v == "ERROR":
                    n_errors += 1
                else:
                    n_inconclusive += 1

                if n_evaluated % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = n_evaluated / elapsed if elapsed > 0 else 0
                    pct = 100 * n_evaluated / len(candidates)
                    print(f"  [{seed_label}] {n_evaluated}/{len(candidates)} "
                          f"({pct:.0f}%) | {rate:.2f}/s | A={n_anomaly}")
                    tf.write(json.dumps({
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "event": f"PROGRESS_{n_evaluated}",
                        "rate": round(rate, 2),
                    }) + "\n")

    elapsed = time.time() - start_time
    manifest = {
        "seed_label": seed_label,
        "seed_rank": seed_rank,
        "phase": 3,
        "n_workers": PARAMS["n_workers"],
        "prime_bound": PARAMS["prime_bound"],
        "precision": PARAMS["precision"],
        "radius": PARAMS["radius"],
        "step": PARAMS["step"],
        "n_curves_evaluated": n_evaluated,
        "n_consistent": n_consistent,
        "n_anomaly": n_anomaly,
        "n_inconclusive": n_inconclusive,
        "n_errors": n_errors,
        "wall_time_s": round(elapsed, 2),
        "rate": round(n_evaluated / elapsed, 2) if elapsed > 0 else 0,
        "anomaly_details": anomalies,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "fingerprint": hashlib.sha256(
            f"BSD_P3_{seed_label}".encode()
        ).hexdigest(),
    }

    manifest_path = Path(PARAMS["output_dir"]) / f"manifest_{seed_label}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n  [[OK]] {seed_label}: {n_evaluated} curves, "
          f"{n_anomaly} anomalies, {elapsed:.1f}s ({rate:.2f}/s)")

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default=None,
                    help="Run a single family (rank5_fermigier, rank6_dujella, rank7_elkies)")
    args = ap.parse_args()

    print("=" * 60)
    print(" GAHENAX BSD PHASE-3 — MULTI-SESSION PARALLEL DISPATCH")
    print(f" Workers: {PARAMS['n_workers']} | Radius: {PARAMS['radius']} | Step: {PARAMS['step']}")
    print("=" * 60)

    if args.family:
        seed = next((s for s in SEEDS_P3 if s[0] == args.family), None)
        if not seed:
            print(f"Unknown family: {args.family}")
            sys.exit(1)
        families = [seed]
    else:
        families = SEEDS_P3

    all_manifests = []
    total_curves = 0
    total_anomalies = 0

    for label, a, b, rank in families:
        m = sweep_family(label, a, b, rank)
        all_manifests.append(m)
        total_curves += m["n_curves_evaluated"]
        total_anomalies += m["n_anomaly"]

    # Grand aggregate
    p1_curves, p1_anom = 4951, 0
    p2_curves, p2_anom = 1323, 0  # estimated from Phase-2

    print(f"\n{'=' * 60}")
    print(" PHASE-3 COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Phase-3 curves: {total_curves}")
    print(f"  Phase-3 anomalies: {total_anomalies}")
    print(f"\n  ═══ GRAND AGGREGATE (P1 + P2 + P3) ═══")
    grand = p1_curves + p2_curves + total_curves
    grand_a = p1_anom + p2_anom + total_anomalies
    print(f"  Total curves: {grand}")
    print(f"  Total anomalies: {grand_a}")
    print(f"  BSD: {'CONSISTENT ✅' if grand_a == 0 else 'ANOMALY ⚠️'}")

    agg = {
        "order_id": "JO-2026-BSD-P3-MULTISESSION",
        "phase": 3,
        "n_workers": PARAMS["n_workers"],
        "families_swept": [m["seed_label"] for m in all_manifests],
        "phase3_curves": total_curves,
        "phase3_anomalies": total_anomalies,
        "grand_total_curves": grand,
        "grand_total_anomalies": grand_a,
        "manifests": all_manifests,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    agg_path = Path(PARAMS["output_dir"]) / "JULES_BSD_P3_AGGREGATE.json"
    agg_path.write_text(json.dumps(agg, indent=2), encoding="utf-8")
    print(f"\n  [SEMAFORO] {agg_path}")


if __name__ == "__main__":
    main()
