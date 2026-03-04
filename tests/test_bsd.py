"""
Test suite for the Gahenax-BSD Falsifiability Search Engine.

Covers: elliptic curves, point arithmetic, L-functions,
rank estimation, and the BSD falsifier pipeline.

Run:
    set PYTHONPATH=.
    pytest tests/test_bsd.py -v
"""
import pytest
import math
from fractions import Fraction

from src.elliptic_curve import EllipticCurve, INFINITY
from src.candidate_generator import (
    generate_neighborhood,
    generate_family_scan,
    estimate_search_space,
    HIGH_RANK_SEEDS,
)
from src.rational_points import (
    find_torsion_points,
    torsion_order,
    search_rational_points,
    estimate_algebraic_rank,
)
from src.l_function import LFunction
from src.rank_estimator import RankEstimator, RankVerdict
from src.experiment_memory import ExperimentMemory


# ===================================================================
# Section 1: Elliptic Curve fundamentals
# ===================================================================

class TestEllipticCurve:

    def test_discriminant_nonzero(self):
        """Valid curve must have Δ ≠ 0."""
        E = EllipticCurve(a=-1, b=0)
        assert E.discriminant != 0

    def test_singular_curve_raises(self):
        """Singular curve (Δ=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Singular"):
            EllipticCurve(a=0, b=0)  # Δ = -16(0+0) = 0

    def test_j_invariant(self):
        """j-invariant for y² = x³ - x: a=-1, b=0."""
        E = EllipticCurve(a=-1, b=0)
        # j = -1728 * (4*(-1))^3 / Δ
        # Δ = -16 * (4*(-1)^3 + 27*0) = -16*(-4) = 64
        # j = -1728 * (-64) / 64 = 1728
        assert E.j_invariant == Fraction(1728)

    def test_point_on_curve(self):
        """Point (0, 0) is on y² = x³ - x  ↔  0 = 0 - 0."""
        E = EllipticCurve(a=-1, b=0)
        assert E.is_on_curve((Fraction(0), Fraction(0)))

    def test_point_not_on_curve(self):
        """Point (1, 1) is NOT on y² = x³ - x  ↔  1 ≠ 0."""
        E = EllipticCurve(a=-1, b=0)
        assert not E.is_on_curve((Fraction(1), Fraction(1)))

    def test_infinity_on_curve(self):
        """Point at infinity is always on the curve."""
        E = EllipticCurve(a=-1, b=0)
        assert E.is_on_curve(INFINITY)

    def test_add_identity(self):
        """P + O = P."""
        E = EllipticCurve(a=-1, b=0)
        P = (Fraction(0), Fraction(0))
        assert E.add(P, INFINITY) == P
        assert E.add(INFINITY, P) == P

    def test_add_inverse(self):
        """P + (-P) = O for a point with y ≠ 0."""
        E = EllipticCurve(a=-1, b=0)
        P = (Fraction(1), Fraction(0))
        neg_P = E.negate(P)
        assert E.add(P, neg_P) == INFINITY

    def test_point_addition(self):
        """Test explicit addition on y² = x³ + 1 (a=0, b=1)."""
        E = EllipticCurve(a=0, b=1)
        # (0, 1) is on the curve: 1 = 0 + 1 ✓
        P = (Fraction(0), Fraction(1))
        assert E.is_on_curve(P)
        # 2P should also be on the curve
        Q = E.add(P, P)
        assert Q != INFINITY
        assert E.is_on_curve(Q)

    def test_scalar_multiplication(self):
        """[n]P should stay on the curve and [0]P = O."""
        E = EllipticCurve(a=0, b=1)
        P = (Fraction(0), Fraction(1))
        assert E.multiply(P, 0) == INFINITY
        for n in [1, 2, 3, 5]:
            Q = E.multiply(P, n)
            if Q != INFINITY:
                assert E.is_on_curve(Q)

    def test_point_counting_small_prime(self):
        """Count |E(F_5)| for y² = x³ + 1."""
        E = EllipticCurve(a=0, b=1)
        count = E.count_points_mod_p(5)
        # Manual check: x=0→y²=1→y=±1(2), x=1→y²=2→no,
        # x=2→y²=9≡4→y=±2(2), x=3→y²=28≡3→no, x=4→y²=65≡0→y=0(1)
        # Total: 1(inf) + 2 + 2 + 1 = 6
        assert count == 6

    def test_a_p_hasse_bound(self):
        """|a_p| ≤ 2√p (Hasse's theorem) for several primes."""
        E = EllipticCurve(a=-1, b=0)
        for p in [5, 7, 11, 13, 17, 19, 23, 29]:
            if E.has_good_reduction_at(p):
                ap = E.a_p(p)
                assert abs(ap) <= 2 * math.sqrt(p) + 0.01, (
                    f"Hasse violation at p={p}: a_p={ap}"
                )

    def test_bad_primes(self):
        """Bad primes of y² = x³ - x should include 2."""
        E = EllipticCurve(a=-1, b=0)
        bad = E.bad_primes(100)
        assert 2 in bad  # Δ = 64 = 2^6, so 2 divides Δ


# ===================================================================
# Section 2: Candidate Generator
# ===================================================================

class TestCandidateGenerator:

    def test_neighborhood_yields_valid_curves(self):
        """All yielded (a,b) should have Δ ≠ 0."""
        count = 0
        for a, b in generate_neighborhood(0, 1, radius=10):
            disc = -16 * (4 * a**3 + 27 * b**2)
            assert disc != 0
            count += 1
        assert count > 0

    def test_family_scan_respects_max(self):
        """Should not yield more than max_curves."""
        candidates = list(generate_family_scan(max_curves=50, radius=5))
        assert len(candidates) <= 50

    def test_search_space_estimate(self):
        """Estimate should match (2r+1)² * n_seeds."""
        est = estimate_search_space(radius=10, n_seeds=3)
        assert est == 3 * (21 ** 2)


# ===================================================================
# Section 3: Rational Points
# ===================================================================

class TestRationalPoints:

    def test_torsion_includes_infinity(self):
        """Torsion points always include the identity O."""
        E = EllipticCurve(a=-1, b=0)
        torsion = find_torsion_points(E)
        assert INFINITY in torsion

    def test_torsion_on_curve(self):
        """All found torsion points must lie on the curve."""
        E = EllipticCurve(a=-1, b=0)
        for pt in find_torsion_points(E):
            assert E.is_on_curve(pt)

    def test_torsion_order_finite(self):
        """Found non-infinity torsion points should have order ≤ 12."""
        E = EllipticCurve(a=-1, b=0)
        torsion = find_torsion_points(E)
        for pt in torsion:
            if pt != INFINITY:
                order = torsion_order(E, pt)
                assert order > 0, f"Point {pt} has order 0 (not torsion?)"
                assert order <= 12

    def test_height_search_finds_known_point(self):
        """y² = x³ + 1 has point (0, 1)."""
        E = EllipticCurve(a=0, b=1)
        pts = search_rational_points(E, height_bound=10)
        found_x0 = any(pt[0] == Fraction(0) for pt in pts)
        assert found_x0, "Should find x=0 point on y²=x³+1"


# ===================================================================
# Section 4: L-function
# ===================================================================

class TestLFunction:

    def test_l_at_one_rank0(self):
        """L(E, 1) should be nonzero for a rank-0 curve (y² = x³ - x)."""
        E = EllipticCurve(a=-1, b=0)
        L = LFunction(E, prime_bound=500, precision=20)
        val = L.at_one()
        assert abs(val) > 0.01, f"L(E,1) = {val}, expected nonzero for rank 0"

    def test_euler_product_converges(self):
        """Product with more primes should give a more stable value."""
        E = EllipticCurve(a=-1, b=0)
        L_small = LFunction(E, prime_bound=100, precision=20)
        L_large = LFunction(E, prime_bound=1000, precision=20)
        val_small = L_small.at_one()
        val_large = L_large.at_one()
        # Both should be nonzero positive for this rank-0 curve
        assert val_small > 0 and val_large > 0
        # Larger product should be in the neighborhood
        assert abs(val_small - val_large) / abs(val_large) < 0.5, (
            f"Euler product diverging: {val_small} vs {val_large}"
        )

    def test_analytic_rank_data_structure(self):
        """analytic_rank_data should return proper structure."""
        E = EllipticCurve(a=-1, b=0)
        L = LFunction(E, prime_bound=200, precision=15)
        data = L.analytic_rank_data(max_order=2)
        assert "L_values" in data
        assert "estimated_rank" in data
        assert 0 in data["L_values"]


# ===================================================================
# Section 5: Rank Estimator
# ===================================================================

class TestRankEstimator:

    def test_rank0_consistent(self):
        """y² = x³ - x (rank 0) should yield CONSISTENT."""
        est = RankEstimator(prime_bound=500, precision=15, height_bound=20)
        verdict = est.analyze(-1, 0)
        assert verdict.verdict in ("CONSISTENT", "INCONCLUSIVE")
        assert verdict.analytic_rank == 0 or verdict.verdict == "INCONCLUSIVE"

    def test_verdict_has_all_fields(self):
        """RankVerdict should be fully populated."""
        est = RankEstimator(prime_bound=200, precision=10, height_bound=10)
        v = est.analyze(0, 1)
        assert v.curve_a == 0
        assert v.curve_b == 1
        assert v.algebraic is not None
        assert v.verdict in ("CONSISTENT", "ANOMALY", "INCONCLUSIVE")
        assert 0.0 <= v.confidence <= 1.0


# ===================================================================
# Section 6: Experiment Memory
# ===================================================================

class TestExperimentMemory:

    def test_save_and_load(self, tmp_path):
        """Save and reload experiment entries."""
        mem = ExperimentMemory(str(tmp_path))
        mem.save_experiment(
            a=-1, b=0, seed_label="test", analytic_rank=0,
            algebraic_lower=0, algebraic_upper=0,
            verdict="CONSISTENT", confidence=0.9,
        )
        entries = mem.load_explored_curves()
        assert len(entries) == 1
        assert entries[0]["verdict"] == "CONSISTENT"

    def test_stats(self, tmp_path):
        """Stats should reflect saved experiments."""
        mem = ExperimentMemory(str(tmp_path))
        mem.save_experiment(
            a=-1, b=0, seed_label="s1", analytic_rank=0,
            algebraic_lower=0, algebraic_upper=0,
            verdict="CONSISTENT", confidence=0.9,
        )
        mem.save_experiment(
            a=0, b=1, seed_label="s2", analytic_rank=1,
            algebraic_lower=0, algebraic_upper=None,
            verdict="ANOMALY", confidence=0.5,
        )
        stats = mem.get_stats()
        assert stats["total"] == 2
        assert stats["anomalies"] == 1
        assert stats["consistent"] == 1
