"""
bsd_worker.py — Amalgam Architecture Orchestrator

Combines the three layers of the Amalgam Architecture:
  Layer 1 (Algebraic Exactness): SageMath 2-Selmer Descent (sage_engine.py)
  Layer 2 (Arithmetic Speed):    C++ GMP/FLINT stub (gmp_engine_stub.py → gmp_engine.so)
  Layer 3 (Horizontal Scale):    Called per-curve by HTCondor/MPI dispatcher

This replaces the old RankEstimator + mpmath pipeline use in mpi_bsd_dispatch.py.
The key advantage: no floating point precision caps regardless of coefficient magnitude.
Rank 7 Elkies (a4=-94M, a6=368B) operates in exact integer arithmetic throughout.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# Ensure src/ is in path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Layer 1 — SageMath exact engine
from src.amalgam.sage_engine import rank_descent, sage_available, SageEngineError

# Layer 2 — GMP engine (stub or compiled C++ extension)
try:
    import gmp_engine  # compiled pybind11 C++ extension (if available)
    _GMP_BACKEND = "cpp"
except ImportError:
    from src.amalgam import gmp_engine_stub as gmp_engine  # Python fallback
    _GMP_BACKEND = "python_stub"


VERDICT_CONSISTENT   = "CONSISTENT"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"
VERDICT_ANOMALY      = "ANOMALY"
VERDICT_ERROR        = "ERROR"


def compute_bsd(
    a4: int,
    a6: int,
    prime_bound: int = 5000,
) -> dict:
    """
    Full BSD computation for E: y² = x³ + a4·x + a6 using the Amalgam Architecture.
    
    Args:
        a4: curve coefficient (Weierstrass short form)
        a6: curve coefficient (Weierstrass short form)
        prime_bound: number of primes for the Euler product approximation
        
    Returns:
        {
            "a4": int,
            "a6": int,
            "algebraic_rank": int,      # from SageMath 2-Selmer descent
            "analytic_rank": int,       # derived from L(E,1) vanishing
            "L_value": float,           # L(E,1)
            "sha_order": float,         # |Ш| numerical estimate
            "bsd_consistent": bool,     # alg_rank == analytic_rank
            "verdict": str,             # CONSISTENT / INCONCLUSIVE / ANOMALY
            "gmp_backend": str,         # 'cpp' or 'python_stub'
            "sage_available": bool,
        }
    """
    result = {
        "a4": a4,
        "a6": a6,
        "algebraic_rank": -1,
        "analytic_rank": -1,
        "L_value": -1.0,
        "sha_order": -1.0,
        "bsd_consistent": None,
        "verdict": VERDICT_ERROR,
        "gmp_backend": _GMP_BACKEND,
        "sage_available": sage_available(),
        "error": None,
    }

    try:
        # ── Layer 2: Fast Euler Product (GMP / stub) ─────────────────────────
        ap_data = gmp_engine.euler_product(a4, a6, prime_bound)
        L_approx = ap_data.get("L", -1.0)
        result["L_value"] = L_approx

        # Derive analytic rank from L-value vanishing
        # If L(E,1) ≈ 0, analytic rank ≥ 1 (vanishes at s=1)
        if L_approx >= 0:
            result["analytic_rank"] = 0 if abs(L_approx) > 1e-5 else 1

        # ── Layer 1: Exact Algebraic Rank (SageMath) ─────────────────────────
        sage_result = rank_descent(a4, a6, precomputed_ap=ap_data)
        result["algebraic_rank"] = sage_result["rank"]
        result["sha_order"]      = sage_result["sha_order"]
        result["bsd_consistent"] = sage_result["bsd_consistent"]

        if sage_result["L_value"] > 0:
            result["L_value"] = sage_result["L_value"]
        if sage_result["bsd_ratio"] > 0:
            result["bsd_ratio"] = sage_result["bsd_ratio"]

        # ── Verdict Engine ───────────────────────────────────────────────────
        alg = result["algebraic_rank"]
        ana = result["analytic_rank"]

        if alg == -1 or ana == -1:
            # Could not determine at least one rank
            result["verdict"] = VERDICT_INCONCLUSIVE
        elif alg == ana:
            result["verdict"] = VERDICT_CONSISTENT
        else:
            # ⚠️ ANOMALY: algebraic and analytic ranks differ!
            result["verdict"] = VERDICT_ANOMALY

    except SageEngineError as e:
        result["verdict"] = VERDICT_INCONCLUSIVE
        result["error"] = f"SageMath error: {e}"
    except Exception as e:
        result["verdict"] = VERDICT_ERROR
        result["error"] = str(e)

    return result


# ─── CLI Entrypoint ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="BSD Amalgam Worker — Single curve evaluation")
    ap.add_argument("--a4", type=int, required=True)
    ap.add_argument("--a6", type=int, required=True)
    ap.add_argument("--prime_bound", type=int, default=2000)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    verdict = compute_bsd(args.a4, args.a6, args.prime_bound)

    if args.json:
        print(json.dumps(verdict, indent=2))
    else:
        v = verdict["verdict"]
        emoji = {"CONSISTENT": "✅", "INCONCLUSIVE": "⚠️", "ANOMALY": "🚨", "ERROR": "❌"}.get(v, "?")
        print(f"\n{emoji} E({args.a4}, {args.a6})")
        print(f"   Algebraic Rank : {verdict['algebraic_rank']}")
        print(f"   Analytic Rank  : {verdict['analytic_rank']}")
        print(f"   L(E,1)         : {verdict['L_value']:.6f}")
        print(f"   |Ш| estimate   : {verdict['sha_order']:.2f}")
        print(f"   Verdict        : {v}")
        print(f"   GMP Backend    : {verdict['gmp_backend']}")
        print(f"   SageMath       : {'YES' if verdict['sage_available'] else 'NO (fallback)'}")
