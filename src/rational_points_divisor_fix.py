# rational_points.py — Divisor fix patch
# Replaces naive discriminant factorization with sympy.factorint to prevent
# the infinite loop on large discriminants.
#
# LAYER:     GEVURAH
# PURPOSE:   Fix _integer_divisors() to use sympy.factorint instead of naive trial division.
# STABILITY: stable

import sympy
from itertools import product
from typing import List

def _integer_divisors(n: int) -> List[int]:
    """Return all positive divisors of |n| using sympy.factorint (no infinite loops)."""
    n = abs(n)
    if n == 0:
        return []
    factors = sympy.factorint(n)
    primes = list(factors.keys())
    powers = [list(range(k + 1)) for k in factors.values()]
    divs = []
    for p in product(*powers):
        d = 1
        for i, exp in enumerate(p):
            d *= primes[i] ** exp
        divs.append(d)
    return sorted(divs)
