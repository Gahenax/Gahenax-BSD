"""
Rank Estimator -- Numerical estimation of ord_{s=1} L(E, s).

Wraps LFunction to classify the analytic rank and compare
against the algebraic rank bounds from rational_points.

Produces a structured RankVerdict used by the BSD Falsifier.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict
from src.elliptic_curve import EllipticCurve
from src.l_function import LFunction
from src.rational_points import estimate_algebraic_rank, RankBounds


# ---------------------------------------------------------------------------
# Verdict types
# ---------------------------------------------------------------------------

@dataclass
class RankVerdict:
    """
    Combined rank analysis for a single curve.

    Fields
    ------
    curve_a, curve_b : int
        Curve coefficients.
    algebraic : RankBounds
        Algebraic rank bounds (from rational point search).
    analytic_rank : int
        Estimated analytic rank (ord_{s=1} L(E,s)).
    L_values : dict
        L(E,1), L'(E,1), etc.
    verdict : str
        'CONSISTENT', 'ANOMALY', 'INCONCLUSIVE'
    confidence : float
        0.0 to 1.0 — how trustworthy is this verdict.
    details : str
        Human-readable explanation.
    """
    curve_a: int
    curve_b: int
    algebraic: RankBounds
    analytic_rank: int
    L_values: Dict[int, float] = field(default_factory=dict)
    verdict: str = "INCONCLUSIVE"
    confidence: float = 0.0
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "curve": {"a": self.curve_a, "b": self.curve_b},
            "algebraic_rank_lower": self.algebraic.lower,
            "algebraic_rank_upper": self.algebraic.upper,
            "analytic_rank": self.analytic_rank,
            "L_values": {str(k): v for k, v in self.L_values.items()},
            "verdict": self.verdict,
            "confidence": self.confidence,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------

class RankEstimator:
    """
    Combines algebraic and analytic rank estimation.

    Parameters
    ----------
    prime_bound : int
        Number of primes for L-function Euler product.
    precision : int
        mpmath decimal precision.
    height_bound : int
        Height bound for rational point search.
    """

    def __init__(
        self,
        prime_bound: int = 2000,
        precision: int = 30,
        height_bound: int = 50,
    ):
        self.prime_bound = prime_bound
        self.precision = precision
        self.height_bound = height_bound

    def analyze(self, a: int, b: int) -> RankVerdict:
        """
        Full rank analysis for curve y² = x³ + ax + b.

        Returns a RankVerdict with verdict:
          - CONSISTENT: algebraic rank bounds contain analytic rank
          - ANOMALY: algebraic and analytic ranks disagree
          - INCONCLUSIVE: not enough data to decide
        """
        curve = EllipticCurve(a, b)

        # --- Algebraic side ---
        alg = estimate_algebraic_rank(curve, self.height_bound)

        # --- Analytic side ---
        L = LFunction(curve, self.prime_bound, self.precision)
        data = L.analytic_rank_data(max_order=4)
        analytic = data["estimated_rank"]

        # --- Verdict ---
        verdict, confidence, details = self._classify(alg, analytic, data)

        return RankVerdict(
            curve_a=a,
            curve_b=b,
            algebraic=alg,
            analytic_rank=analytic,
            L_values=data["L_values"],
            verdict=verdict,
            confidence=confidence,
            details=details,
        )

    def _classify(
        self,
        alg: RankBounds,
        analytic: int,
        data: dict,
    ) -> tuple:
        """
        Classify the relationship between algebraic and analytic rank.

        Returns (verdict, confidence, details).
        """
        if analytic < 0:
            return (
                "INCONCLUSIVE",
                0.0,
                f"Analytic rank indeterminate (L derivatives below epsilon "
                f"up to order {len(data['L_values'])-1}). "
                f"Needs higher precision or more primes.",
            )

        # Case 1: Exact algebraic rank known
        if alg.is_exact:
            if alg.exact == analytic:
                return (
                    "CONSISTENT",
                    0.9,
                    f"rank_alg = rank_an = {analytic}. "
                    f"BSD consistent.",
                )
            else:
                return (
                    "ANOMALY",
                    self._anomaly_confidence(alg, analytic, data),
                    f"POTENTIAL BSD VIOLATION: "
                    f"rank_algebraic = {alg.exact}, "
                    f"rank_analytic = {analytic}. "
                    f"Requires independent verification.",
                )

        # Case 2: Only bounds known
        if alg.upper is not None:
            if alg.lower <= analytic <= alg.upper:
                return (
                    "CONSISTENT",
                    0.6,
                    f"rank_an = {analytic} within algebraic bounds "
                    f"[{alg.lower}, {alg.upper}]. BSD plausible.",
                )
            else:
                return (
                    "ANOMALY",
                    self._anomaly_confidence(alg, analytic, data),
                    f"POTENTIAL BSD VIOLATION: "
                    f"rank_analytic = {analytic} outside "
                    f"algebraic bounds [{alg.lower}, {alg.upper}].",
                )
        else:
            # Only lower bound known — from heuristic height search,
            # NOT from proper descent. Independence of generators is
            # not proven, so we CANNOT claim ANOMALY here.
            if analytic >= alg.lower:
                return (
                    "CONSISTENT",
                    0.4,
                    f"rank_an = {analytic} ≥ algebraic lower bound "
                    f"{alg.lower}. BSD not contradicted (upper unknown).",
                )
            else:
                # Downgrade to INCONCLUSIVE: the height search may have
                # found dependent points or missed torsion of high order.
                # True anomalies require exact rank from 2-Selmer descent.
                return (
                    "INCONCLUSIVE",
                    0.15,
                    f"rank_analytic = {analytic} < heuristic lower bound "
                    f"{alg.lower}, but algebraic rank is from height search "
                    f"only (no descent). Needs exact rank computation "
                    f"(SageMath/PARI) to confirm or dismiss.",
                )

    def _anomaly_confidence(
        self,
        alg: RankBounds,
        analytic: int,
        data: dict,
    ) -> float:
        """
        Estimate confidence that an anomaly is real (vs numerical error).

        Higher confidence if:
          - Algebraic rank is exact (from descent, not just search)
          - L-function values are well-separated from zero
          - More primes used in Euler product
        """
        conf = 0.3  # Base — we're always cautious

        # Bonus if algebraic rank is exact
        if alg.is_exact:
            conf += 0.2

        # Bonus if |L^(n)(E,1)| is well above epsilon
        epsilon = data.get("epsilon", 1e-10)
        for n, val in data["L_values"].items():
            if abs(val) > 100 * epsilon:
                conf += 0.05  # Well-separated value
                break

        return min(conf, 0.8)  # Never exceed 0.8 without independent verification
