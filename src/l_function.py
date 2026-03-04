"""
L-function Engine -- Euler product computation of L(E, s).

Computes L(E, s) = ∏_{p good} (1 - a_p·p^{-s} + p^{1-2s})^{-1}
via partial Euler product with configurable prime bound.

Uses mpmath for arbitrary-precision evaluation near s=1.
"""
import math
from typing import Tuple, Optional, List
from sympy import primerange
import mpmath


# ---------------------------------------------------------------------------
# Euler product
# ---------------------------------------------------------------------------

def euler_factor(a_p: int, p: int, s: complex) -> complex:
    """
    Compute the local Euler factor at a good prime p:

        L_p(s) = (1 - a_p · p^{-s} + p^{1-2s})^{-1}

    Parameters
    ----------
    a_p : int
        Trace of Frobenius at p.
    p : int
        Prime.
    s : complex
        Point of evaluation.
    """
    p_neg_s = mpmath.power(p, -s)
    p_1_2s = mpmath.power(p, 1 - 2 * s)
    denom = 1 - a_p * p_neg_s + p_1_2s
    if abs(denom) < 1e-100:
        return mpmath.mpf(1)  # Degenerate — skip
    return 1 / denom


def euler_factor_bad(a_p: int, p: int, s: complex) -> complex:
    """
    Euler factor at a bad prime (simplified):

        L_p(s) = (1 - a_p · p^{-s})^{-1}

    For bad primes, a_p ∈ {-1, 0, 1} depending on reduction type.
    """
    p_neg_s = mpmath.power(p, -s)
    denom = 1 - a_p * p_neg_s
    if abs(denom) < 1e-100:
        return mpmath.mpf(1)
    return 1 / denom


class LFunction:
    """
    L-function of an elliptic curve E: y² = x³ + ax + b.

    Computes L(E, s) via partial Euler product up to prime_bound.

    Parameters
    ----------
    curve : EllipticCurve
        The elliptic curve.
    prime_bound : int
        Compute Euler product using primes up to this bound.
    precision : int
        mpmath decimal precision (dps).
    """

    def __init__(self, curve, prime_bound: int = 5000, precision: int = 50):
        from src.elliptic_curve import EllipticCurve
        self.curve: EllipticCurve = curve
        self.prime_bound = prime_bound
        self.precision = precision

        # Precompute a_p values and reduction type
        self._primes = list(primerange(2, prime_bound))
        self._a_p_values = {}
        self._good_reduction = {}
        for p in self._primes:
            self._good_reduction[p] = curve.has_good_reduction_at(p)
            self._a_p_values[p] = curve.a_p(p)

    @property
    def n_primes(self) -> int:
        """Number of primes used in the Euler product."""
        return len(self._primes)

    def evaluate(self, s: complex) -> complex:
        """
        Evaluate L(E, s) at point s using the partial Euler product.

        Parameters
        ----------
        s : complex
            Point of evaluation.  BSD focuses on s = 1.
        """
        mpmath.mp.dps = self.precision
        product = mpmath.mpf(1)

        for p in self._primes:
            a_p = self._a_p_values[p]
            if self._good_reduction[p]:
                factor = euler_factor(a_p, p, s)
            else:
                factor = euler_factor_bad(a_p, p, s)
            product *= factor

        return complex(product)

    def at_one(self) -> float:
        """
        Evaluate L(E, 1).

        BSD predicts:
          - rank 0  →  L(E,1) ≠ 0
          - rank ≥ 1 →  L(E,1) = 0
        """
        mpmath.mp.dps = self.precision
        val = self.evaluate(1.0)
        return float(val.real)

    def derivative_at_one(self, order: int = 1, h: float = 1e-6) -> float:
        """
        Estimate the n-th derivative of L(E, s) at s=1
        using centered finite differences.

        Parameters
        ----------
        order : int
            Order of derivative (1, 2, 3, ...).
        h : float
            Step size for finite differences.
        """
        mpmath.mp.dps = self.precision

        if order == 1:
            f_plus = self.evaluate(1.0 + h)
            f_minus = self.evaluate(1.0 - h)
            return float((f_plus.real - f_minus.real) / (2 * h))
        elif order == 2:
            f_plus = self.evaluate(1.0 + h)
            f_zero = self.evaluate(1.0)
            f_minus = self.evaluate(1.0 - h)
            return float(
                (f_plus.real - 2 * f_zero.real + f_minus.real) / (h * h)
            )
        else:
            # General n-th order via recursive finite differences
            # Use Richardson extrapolation for higher orders
            coeffs = _finite_diff_coefficients(order)
            result = 0.0
            for k, c in enumerate(coeffs):
                shift = (k - order) * h
                val = self.evaluate(1.0 + shift)
                result += c * val.real
            return float(result / (h ** order))

    def analytic_rank_data(
        self,
        max_order: int = 4,
        h: float = 1e-5,
    ) -> dict:
        """
        Compute L(E,1) and its derivatives to estimate the analytic rank.

        Returns a dict with:
          - 'L_values': {0: L(E,1), 1: L'(E,1), 2: L''(E,1), ...}
          - 'estimated_rank': first order where |L^(n)(E,1)| > epsilon
          - 'epsilon': threshold used
        """
        epsilon = 10 ** (-self.precision // 4)
        values = {}

        for n in range(max_order + 1):
            if n == 0:
                values[n] = self.at_one()
            else:
                values[n] = self.derivative_at_one(n, h)

        # Estimate rank = first n where |L^(n)| > epsilon
        estimated_rank = None
        for n in range(max_order + 1):
            if abs(values[n]) > epsilon:
                estimated_rank = n
                break

        if estimated_rank is None:
            estimated_rank = -1  # Indeterminate (exceeds max_order)

        return {
            "L_values": values,
            "estimated_rank": estimated_rank,
            "epsilon": epsilon,
        }


# ---------------------------------------------------------------------------
# Finite difference coefficients (internal)
# ---------------------------------------------------------------------------

def _finite_diff_coefficients(order: int) -> List[float]:
    """
    Central finite difference coefficients for the n-th derivative.

    Returns coefficients c_k such that:
        f^(n)(x) ≈ (1/h^n) Σ c_k · f(x + k·h)
    """
    # Standard central difference stencils
    stencils = {
        1: [-0.5, 0, 0.5],
        2: [1, -2, 1],
        3: [-0.5, 1, 0, -1, 0.5],
        4: [1, -4, 6, -4, 1],
    }
    if order in stencils:
        return stencils[order]
    # Fallback: use order+1 point stencil (less accurate)
    import numpy as np
    n = order + 1 + (order % 2)
    mid = n // 2
    coeffs = [0.0] * n
    coeffs[0] = 1.0
    for _ in range(order):
        new = [0.0] * n
        for i in range(n - 1):
            new[i] = coeffs[i + 1] - coeffs[i]
        coeffs = new
    return coeffs
