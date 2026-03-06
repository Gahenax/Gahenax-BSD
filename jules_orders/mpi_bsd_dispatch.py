"""
MPI Multi-Node Dispatch for Gahenax-BSD.

This script replaces `ProcessPoolExecutor` with `mpi4py` to allow the
BSD sweep to scale across an arbitrary number of PHYSICAL nodes in a 
Supercomputing cluster (SLURM, PBS, etc.).

Requirements:
    pip install mpi4py

Usage (via mpirun or srun on the cluster):
    # For 4-core machines (e.g., Jules default): use -np 4, NOT -np 8
    # --oversubscribe causes cache contention and slows down integer descent significantly.
    mpirun -np 4 python jules_orders/mpi_bsd_dispatch.py --family rank7_elkies
    # For supercomputing clusters (SLURM/PBS): scale freely to 128+
    mpirun -np 128 python jules_orders/mpi_bsd_dispatch.py --family rank7_elkies
"""
import sys
import os
import json
import time
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

try:
    from mpi4py import MPI
except ImportError:
    print("FATAL: mpi4py is required for Multi-Node Supercomputing Dispatch.")
    print("Please install with: pip install mpi4py")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.rank_estimator import RankEstimator

SEEDS = {
    "rank5_fermigier": (-879984, 319138704, 5),
    "rank6_dujella": (-3674496, 2706752832, 6),
    "rank7_elkies": (-94816050, 368541849450, 7),
}

# ---------------------------------------------------------------------------
# Worker Logic (runs independently on each core)
# ---------------------------------------------------------------------------
def evaluate_single_curve(a, b, seed_label, seed_rank, params):
    try:
        estimator = RankEstimator(
            prime_bound=params["prime_bound"],
            precision=params["precision"],
            height_bound=params["height_bound"],
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
# MPI Orchestrator Logic
# ---------------------------------------------------------------------------
def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()   # My process ID (e.g., 0 to N-1)
    size = comm.Get_size()   # Total number of workers across ALL physical nodes

    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, help="Family name (e.g., rank7_elkies)")
    ap.add_argument("--radius", type=int, default=100, help="Search radius")
    ap.add_argument("--step", type=int, default=10, help="Search step size")
    # Reduced defaults per Jules analysis: prime_bound=500, precision=20 is sufficient
    # to distinguish vanishing order for Rank 7 without hanging on large coefficients.
    # Use prime_bound=5000 / precision=35 only on supercomputing nodes with >8 cores.
    ap.add_argument("--prime_bound", type=int, default=500, help="Primes bound (500 sufficient for rank detection)")
    ap.add_argument("--precision", type=int, default=20, help="DPS precision (20 sufficient for vanishing order)")
    ap.add_argument("--height_bound", type=int, default=30)
    args = ap.parse_args()

    if args.family not in SEEDS:
        if rank == 0:
            print(f"Unknown family: {args.family}")
        sys.exit(1)

    base_a, base_b, seed_rank = SEEDS[args.family]
    params = vars(args)

    # -----------------------------------------------------------------------
    # NODE 0: Generate universe and partition it for the cluster
    # -----------------------------------------------------------------------
    if rank == 0:
        print("=" * 70)
        print(f" GAHENAX MPI SUPERCOMPUTING DISPATCH")
        print(f" Probing: {args.family} | Radius: {args.radius} | Step: {args.step}")
        print(f" Cluster Active Workers (across all physical nodes): {size}")
        print("=" * 70)

        all_candidates = []
        for da in range(-args.radius, args.radius + 1, args.step):
            for db in range(-args.radius, args.radius + 1, args.step):
                a = base_a + da
                b = base_b + db
                if (-16 * (4 * a**3 + 27 * b**2)) != 0:
                    all_candidates.append((a, b))

        print(f"[MPI Master] Total curves to evaluate: {len(all_candidates)}")
        start_time = time.time()

        # Split the universe into 'size' roughly equal chunks
        # e.g., if array has 1000 items and size is 100, each chunk gets 10 items
        chunks = [all_candidates[i::size] for i in range(size)]
    else:
        chunks = None

    # -----------------------------------------------------------------------
    # SCATTER: Master distributes chunks to all workers via the network
    # -----------------------------------------------------------------------
    my_chunk = comm.scatter(chunks, root=0)

    # -----------------------------------------------------------------------
    # PROCESS: All nodes work concurrently in isolated memory spaces
    # -----------------------------------------------------------------------
    # Per-curve checkpointing: write results to disk immediately after each curve.
    # This ensures no data is lost if the session times out before the MPI gather.
    checkpoint_dir = Path("evidence/supercomputing/checkpoints")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = checkpoint_dir / f"worker_{rank}_{args.family}.jsonl"

    local_results = []
    local_anomalies = 0
    for a, b in my_chunk:
        verdict = evaluate_single_curve(a, b, args.family, seed_rank, params)
        local_results.append(verdict)

        # Checkpoint: write this result immediately to disk (BEFORE gather)
        with open(checkpoint_file, "a", encoding="utf-8") as ckpt:
            ckpt.write(json.dumps(verdict) + "\n")

        if verdict["verdict"] == "ANOMALY":
            local_anomalies += 1
            print(f"[Worker {rank}] ⚠️ ANOMALY FOUND ON SEED E({a},{b})!", flush=True)
        else:
            print(f"[Worker {rank}] curve E({a},{b}) → {verdict['verdict']}", flush=True)

    # -----------------------------------------------------------------------
    # GATHER: Master node collects all chunks back from the network
    # -----------------------------------------------------------------------
    all_results_lists = comm.gather(local_results, root=0)

    # -----------------------------------------------------------------------
    # NODE 0: Aggregation and Ledger commitment
    # -----------------------------------------------------------------------
    if rank == 0:
        elapsed = time.time() - start_time
        all_results = [item for sublist in all_results_lists for item in sublist]

        n_evaluated = len(all_results)
        n_consistent = sum(1 for r in all_results if r["verdict"] == "CONSISTENT")
        n_anomalies = sum(1 for r in all_results if r["verdict"] == "ANOMALY")
        n_inconclusive = sum(1 for r in all_results if r["verdict"] == "INCONCLUSIVE")
        n_errors = sum(1 for r in all_results if r["verdict"] == "ERROR")

        out_dir = Path("evidence/supercomputing")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        manifest = {
            "cluster_size": size,
            "architecture": "MPI (Multi-Node)",
            "seed_label": args.family,
            "seed_rank": seed_rank,
            "n_curves_evaluated": n_evaluated,
            "n_consistent": n_consistent,
            "n_anomalies": n_anomalies,
            "n_inconclusive": n_inconclusive,
            "n_errors": n_errors,
            "wall_time_s": round(elapsed, 2),
            "curves_per_second": round(n_evaluated / elapsed, 2) if elapsed > 0 else 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Save manifest
        mf_path = out_dir / f"mpi_manifest_{args.family}.json"
        mf_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Save all results (telemetry)
        tel_path = out_dir / f"mpi_telemetry_{args.family}.jsonl"
        with open(tel_path, "w", encoding="utf-8") as f:
            for r in all_results:
                f.write(json.dumps(r) + "\n")

        print(f"\n{'=' * 70}")
        print(f" MPI RUN COMPLETE")
        print(f" Curves: {n_evaluated} | Anomalies: {n_anomalies}")
        print(f" Total Time: {elapsed:.1f}s | Rate: {n_evaluated/elapsed:.2f}/s")
        print(f" Evidence saved to: {out_dir}")
        print(f" {'=' * 70}")

if __name__ == "__main__":
    main()
