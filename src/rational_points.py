"""
Rational Point Search -- Algebraic rank estimation via point discovery.

Implements:
  - Nagell-Lutz theorem: finds torsion points with integral coordinates
  - Height-bounded search: brute-force rational points up to height H
  - Rank bounds: lower bound from independent points found

The algebraic rank r(E(Q)) is the number of independent rational points
of infinite order. We compute a lower bound by finding actual points,
and an upper bound heuristic via torsion structure.
"""
import math
from typing import List, Tuple, Optional
from fractions import Fraction
from src.elliptic_curve import EllipticCurve, INFINITY, Point, _frac


# ---------------------------------------------------------------------------
# Nagell-Lutz torsion search
# ---------------------------------------------------------------------------

def _integer_divisors(n: int) -> List[int]:
    """Return all positive divisors of |n|."""
    n = abs(n)
    if n == 0:
        return []
    divs = []
    for i in range(1, int(math.isqrt(n)) + 1):
        if n % i == 0:
            divs.append(i)
            if i != n // i:
                divs.append(n // i)
    return sorted(divs)


def find_torsion_points(curve: EllipticCurve) -> List:
    """
    Apply Nagell-Lutz theorem to find torsion points with integer coords.

    Theorem: If (x, y) is a torsion point of finite order on E: y² = x³+ax+b
    with a,b ∈ Z, then x,y ∈ Z and either y=0 or y² | Δ.

    Returns list of affine points (as Fraction tuples) + INFINITY.
    """
    disc = curve.discriminant
    torsion = [INFINITY]

    # Candidate y values: y=0 or y² | disc
    candidate_y2 = set()
    candidate_y2.add(0)
    for d in _integer_divisors(disc):
        # y² = d  →  y = ±√d if d is perfect square
        sqrt_d = int(math.isqrt(d))
        if sqrt_d * sqrt_d == d:
            candidate_y2.add(sqrt_d)
            candidate_y2.add(-sqrt_d)

    # For each candidate y, solve x³ + ax + b - y² = 0 for integer x
    a, b = curve.a, curve.b
    for y in candidate_y2:
        target = y * y  # x³ + ax + b = y²
        # Brute-force x in a reasonable range
        # By Nagell-Lutz, |x| is bounded, but we use a practical limit
        x_bound = max(int(abs(target) ** (1/3)) + 10, 100)
        for x in range(-x_bound, x_bound + 1):
            if x**3 + a * x + b == target:
                pt = (Fraction(x), Fraction(y))
                if curve.is_on_curve(pt):
                    torsion.append(pt)

    return torsion


def torsion_order(curve: EllipticCurve, P) -> int:
    """
    Compute the order of point P in E(Q)_tors.

    Returns n such that [n]P = O, or 0 if order > 12
    (by Mazur's theorem, torsion order ≤ 12).
    """
    if P == INFINITY:
        return 1
    Q = P
    for n in range(2, 13):
        Q = curve.add(Q, P)
        if Q == INFINITY:
            return n
    return 0  # Not torsion (infinite order) or order > 12


# ---------------------------------------------------------------------------
# Height-bounded rational point search
# ---------------------------------------------------------------------------

def search_rational_points(
    curve: EllipticCurve,
    height_bound: int = 100,
) -> List:
    """
    Brute-force search for rational points (x, y) with x = p/q,
    |p| ≤ H, 1 ≤ q ≤ H.

    This finds points of small naive height. For high-rank curves,
    generators may have large height and escape this search.

    Returns list of affine points found.
    """
    found = []
    for q in range(1, height_bound + 1):
        for p in range(-height_bound, height_bound + 1):
            x = Fraction(p, q)
            # y² = x³ + ax + b
            rhs = x**3 + curve.a * x + curve.b
            if rhs < 0:
                continue
            if rhs == 0:
                pt = (x, Fraction(0))
                if pt not in found:
                    found.append(pt)
                continue
            # Check if rhs is a perfect square of a rational
            # rhs = num/den → need num*den to be a perfect square
            num = rhs.numerator
            den = rhs.denominator
            product = num * den
            sqrt_prod = int(math.isqrt(product))
            if sqrt_prod * sqrt_prod == product:
                y = Fraction(sqrt_prod, den)
                pt_pos = (x, y)
                pt_neg = (x, -y)
                if pt_pos not in found:
                    found.append(pt_pos)
                if y != 0 and pt_neg not in found:
                    found.append(pt_neg)

    return found


# ---------------------------------------------------------------------------
# Rank bounds
# ---------------------------------------------------------------------------

class RankBounds:
    """
    Tracks algebraic rank bounds for a curve.

    Attributes
    ----------
    lower : int
        Number of independent non-torsion points found.
    upper : int or None
        Upper bound (None = unknown).
    generators : list
        Independent generators found so far.
    """

    def __init__(self):
        self.lower = 0
        self.upper = None
        self.generators: List = []
        self.torsion_points: List = []

    @property
    def is_exact(self) -> bool:
        """True if lower == upper (rank exactly determined)."""
        return self.upper is not None and self.lower == self.upper

    @property
    def exact(self) -> Optional[int]:
        """Return exact rank if known, else None."""
        return self.lower if self.is_exact else None

    def __repr__(self) -> str:
        ub = self.upper if self.upper is not None else "?"
        return f"RankBounds(lower={self.lower}, upper={ub})"


def estimate_algebraic_rank(
    curve: EllipticCurve,
    height_bound: int = 100,
) -> RankBounds:
    """
    Estimate the algebraic rank by finding torsion + free points.

    Strategy:
    1. Find torsion via Nagell-Lutz
    2. Find rational points via height-bounded search
    3. Filter out torsion → remaining are candidates for free part
    4. lower_bound = # independent non-torsion points (heuristic)

    This is a LOWER BOUND. For higher-rank curves (r ≥ 3),
    generators often have height >> search bound.
    """
    bounds = RankBounds()

    # Step 1: Torsion
    torsion = find_torsion_points(curve)
    bounds.torsion_points = torsion

    # Step 2: Height search
    all_points = search_rational_points(curve, height_bound)

    # Step 3: Filter torsion
    torsion_set = set()
    for t in torsion:
        if t != INFINITY:
            torsion_set.add(t)

    free_candidates = []
    for pt in all_points:
        if pt not in torsion_set:
            # Check it's not torsion by computing order
            order = torsion_order(curve, pt)
            if order == 0:  # Infinite order → free part
                free_candidates.append(pt)

    # Step 4: Assign as generators (heuristic independence)
    # True independence requires checking linear dependence in E(Q),
    # which needs descent. We use a simple heuristic: distinct x-coords.
    seen_x = set()
    for pt in free_candidates:
        if pt[0] not in seen_x:
            bounds.generators.append(pt)
            seen_x.add(pt[0])

    bounds.lower = len(bounds.generators)
    return bounds
