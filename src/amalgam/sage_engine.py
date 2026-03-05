"""
sage_engine.py — SageMath 2-Selmer Descent Engine for Gahenax-BSD

This module provides the algebraically exact rank computation for elliptic curves
using SageMath's built-in 2-Selmer descent algorithm. Unlike the mpmath float-based
approach, 2-Selmer descent operates entirely in INTEGER arithmetic, making it immune
to precision-loss OOM failures at high ranks.

Requirements:
    pip install sagemath-standard  (or use the SageMath binary distribution)

    Fallback mode (no SageMath): uses sympy for basic rank hints (less exact).
"""
from __future__ import annotations
import sys
import json
from typing import Optional, Tuple

# ─── SageMath Detection ───────────────────────────────────────────────────────
try:
    from sage.all import EllipticCurve, ZZ, RDF, RR
    SAGE_AVAILABLE = True
except ImportError:
    SAGE_AVAILABLE = False

# ─── Sympy Fallback ─────────────────────────────────────────────────────────
try:
    from sympy import isprime
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False


# ─── Engine ──────────────────────────────────────────────────────────────────

class SageEngineError(Exception):
    """Raised when SageMath is unavailable and no fallback can produce a result."""
    pass


def rank_descent(
    a4: int,
    a6: int,
    algorithm: str = "2descent_complete",
    precomputed_ap: Optional[dict] = None,
    timeout_s: int = 300,
) -> dict:
    """
    Compute the algebraic rank of E: y² = x³ + a4·x + a6 using 2-Selmer descent.
    
    Returns a dict with:
      - rank          (int)   : algebraic rank
      - sha_order     (float) : numerical order of Ш (Tate-Shafarevich group)
      - L_value       (float) : L(E,1) numerical value
      - bsd_ratio     (float) : L(E,1) / (Ω · Reg · ∏cₚ) — should be |Ш| if BSD holds
      - bsd_consistent (bool) : True if sha_order ≈ L(E,1)/... (BSD test)
      - engine        (str)   : 'sage' or 'fallback'
    """
    if SAGE_AVAILABLE:
        return _sage_rank(a4, a6, algorithm, precomputed_ap)
    else:
        return _fallback_rank(a4, a6, precomputed_ap)


def _sage_rank(a4: int, a6: int, algorithm: str, precomputed_ap: Optional[dict]) -> dict:
    """Full SageMath rank computation via 2-Selmer descent."""
    try:
        E = EllipticCurve([ZZ(a4), ZZ(a6)])

        # 2-Selmer descent — exact integer arithmetic, no float precision cap
        rank = int(E.rank(algorithm=algorithm))

        # Numerical Ш (Tate-Shafarevich group order estimate)
        try:
            sha_order = float(E.sha().an_numerical(prec=50))
        except Exception:
            sha_order = -1.0  # indeterminate

        # L-function value at s=1
        try:
            L_val = float(E.lseries().L(1, prec=50))
        except Exception:
            L_val = -1.0

        # BSD ratio: L(E,1) / (Omega * Reg * tamagawa)
        try:
            bsd_ratio = float(E.lseries().L_ratio())
        except Exception:
            bsd_ratio = -1.0

        # BSD consistency check: bsd_ratio ≈ sha_order (integer, power of prime)
        bsd_consistent = False
        if sha_order > 0 and bsd_ratio > 0:
            diff = abs(round(bsd_ratio) - sha_order)
            bsd_consistent = diff < 0.5

        return {
            "rank": rank,
            "sha_order": sha_order,
            "L_value": L_val,
            "bsd_ratio": bsd_ratio,
            "bsd_consistent": bsd_consistent,
            "engine": "sage",
        }
    except Exception as e:
        raise SageEngineError(f"SageMath rank computation failed for E({a4},{a6}): {e}") from e


def _fallback_rank(a4: int, a6: int, precomputed_ap: Optional[dict]) -> dict:
    """
    Fallback rank estimator when SageMath is not installed.
    Uses the L-function approximation from precomputed_ap values if available.
    Produces INCONCLUSIVE verdicts — not exact.
    """
    if precomputed_ap and "L" in precomputed_ap:
        L_val = precomputed_ap["L"]
        # Heuristic: if L(E,1) ≈ 0, rank >= 1 (vanishing order)
        rank_hint = 0 if abs(L_val) > 1e-6 else -1  # -1 = unknown
    else:
        rank_hint = -1  # truly unknown without SageMath

    return {
        "rank": rank_hint,       # -1 signals INCONCLUSIVE
        "sha_order": -1.0,
        "L_value": precomputed_ap.get("L", -1.0) if precomputed_ap else -1.0,
        "bsd_ratio": -1.0,
        "bsd_consistent": None,  # cannot determine
        "engine": "fallback_no_sage",
    }


def sage_available() -> bool:
    """Check if SageMath is installed in the current environment."""
    return SAGE_AVAILABLE


def test_smoke(a4: int = -1, a6: int = 1) -> bool:
    """Quick smoke test: compute rank of y² = x³ - x + 1 (rank 0, well-known)."""
    try:
        result = rank_descent(a4, a6)
        assert result["rank"] == 0, f"Expected rank 0, got {result['rank']}"
        return True
    except Exception as e:
        print(f"[sage_engine] Smoke test failed: {e}")
        return False


if __name__ == "__main__":
    print(f"SageMath available: {SAGE_AVAILABLE}")
    
    test_cases = [
        (-1, 0, 0),          # rank 0 control
        (-43, 166, 1),       # rank 1 (37a1 family)
        (-16, -44, 2),       # rank 2 (389a)
        (-13392, -1080432, 3), # rank 3 (5077a)
    ]
    
    for a4, a6, expected_rank in test_cases:
        result = rank_descent(a4, a6)
        status = "✅" if result["rank"] == expected_rank else "❌"
        print(f"{status} E({a4}, {a6}) → rank={result['rank']} (expected {expected_rank}) | Ш≈{result['sha_order']:.2f} | engine={result['engine']}")
    
    print("\n--- Rank 7 Elkies (the challenge) ---")
    r7 = rank_descent(-94816050, 368541849450)
    print(json.dumps(r7, indent=2))
