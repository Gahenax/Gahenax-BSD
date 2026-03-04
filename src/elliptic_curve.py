"""
Elliptic Curve Engine -- Short Weierstrass model E: y² = x³ + ax + b.

Implements:
  - Discriminant, j-invariant, conductor estimation
  - Affine point arithmetic on E(Q)
  - Reduction mod p: point counting via naive enumeration
  - Trace of Frobenius a_p = p + 1 - |E(F_p)|
"""
import math
from typing import Optional, Tuple, List
from fractions import Fraction


# ---------------------------------------------------------------------------
# Point representation
# ---------------------------------------------------------------------------

INFINITY = "O"  # The identity element (point at infinity)

Point = Tuple[Fraction, Fraction]  # Affine point (x, y)


def _frac(v) -> Fraction:
    """Coerce int/float to Fraction cleanly."""
    if isinstance(v, Fraction):
        return v
    return Fraction(v)


# ---------------------------------------------------------------------------
# Curve class
# ---------------------------------------------------------------------------

class EllipticCurve:
    """
    Short Weierstrass form: y² = x³ + a·x + b  over Q.

    Parameters
    ----------
    a, b : int
        Integer coefficients of the curve.

    Raises
    ------
    ValueError
        If the discriminant is zero (singular curve).
    """

    def __init__(self, a: int, b: int):
        self.a = a
        self.b = b
        self._disc = -16 * (4 * a**3 + 27 * b**2)
        if self._disc == 0:
            raise ValueError(
                f"Singular curve: Δ = 0 for (a={a}, b={b}). "
                "Not an elliptic curve."
            )

    # -- Invariants --------------------------------------------------------

    @property
    def discriminant(self) -> int:
        """Discriminant Δ = -16(4a³ + 27b²). Must be ≠ 0."""
        return self._disc

    @property
    def j_invariant(self) -> Fraction:
        """j-invariant j = -1728 · (4a)³ / Δ."""
        numerator = -1728 * (4 * self.a) ** 3
        return Fraction(numerator, self._disc)

    def is_smooth(self) -> bool:
        """True if the curve is non-singular (Δ ≠ 0)."""
        return self._disc != 0

    # -- Point arithmetic on E(Q) -----------------------------------------

    def is_on_curve(self, P) -> bool:
        """Check if point P lies on E."""
        if P == INFINITY:
            return True
        x, y = _frac(P[0]), _frac(P[1])
        lhs = y ** 2
        rhs = x ** 3 + self.a * x + self.b
        return lhs == rhs

    def negate(self, P) -> object:
        """Return -P on E."""
        if P == INFINITY:
            return INFINITY
        x, y = _frac(P[0]), _frac(P[1])
        return (x, -y)

    def add(self, P, Q) -> object:
        """
        Add two points P + Q on E using the chord-and-tangent law.

        Returns INFINITY (identity) or an affine (x, y) Fraction tuple.
        """
        if P == INFINITY:
            return Q
        if Q == INFINITY:
            return P

        x1, y1 = _frac(P[0]), _frac(P[1])
        x2, y2 = _frac(Q[0]), _frac(Q[1])

        if x1 == x2:
            if y1 == -y2:
                return INFINITY  # P + (-P) = O
            # P == Q  →  point doubling
            if y1 == 0:
                return INFINITY  # tangent is vertical
            lam = Fraction(3 * x1**2 + self.a, 2 * y1)
        else:
            lam = Fraction(y2 - y1, x2 - x1)

        x3 = lam**2 - x1 - x2
        y3 = lam * (x1 - x3) - y1
        return (x3, y3)

    def multiply(self, P, n: int) -> object:
        """Scalar multiplication [n]P via double-and-add."""
        if n == 0 or P == INFINITY:
            return INFINITY
        if n < 0:
            return self.multiply(self.negate(P), -n)

        result = INFINITY
        addend = P
        while n > 0:
            if n & 1:
                result = self.add(result, addend)
            addend = self.add(addend, addend)
            n >>= 1
        return result

    # -- Reduction mod p ---------------------------------------------------

    def count_points_mod_p(self, p: int) -> int:
        """
        Count |E(F_p)| by naive enumeration.

        Includes the point at infinity.
        """
        count = 1  # point at infinity
        for x in range(p):
            rhs = (x**3 + self.a * x + self.b) % p
            # Check if rhs is a quadratic residue mod p
            if rhs == 0:
                count += 1  # y = 0
            elif pow(rhs, (p - 1) // 2, p) == 1:
                count += 2  # ±y
        return count

    def a_p(self, p: int) -> int:
        """
        Trace of Frobenius: a_p = p + 1 - |E(F_p)|.

        By Hasse's theorem: |a_p| ≤ 2√p.
        """
        return p + 1 - self.count_points_mod_p(p)

    def has_good_reduction_at(self, p: int) -> bool:
        """True if p does not divide Δ (good reduction)."""
        return self._disc % p != 0

    def bad_primes(self, limit: int = 1000) -> List[int]:
        """Return primes of bad reduction up to limit."""
        from sympy import primerange
        return [p for p in primerange(2, limit)
                if not self.has_good_reduction_at(p)]

    # -- Display -----------------------------------------------------------

    def __repr__(self) -> str:
        return f"EllipticCurve(a={self.a}, b={self.b})"

    def __str__(self) -> str:
        a_str = f"{self.a:+d}" if self.a != 0 else ""
        b_str = f"{self.b:+d}" if self.b != 0 else ""
        terms = "x³"
        if self.a != 0:
            terms += f" {a_str}·x"
        if self.b != 0:
            terms += f" {b_str}"
        return f"y² = {terms}"
