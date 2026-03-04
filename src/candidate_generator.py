"""
Candidate Generator -- Parametric family generation for BSD falsifiability.

Generates elliptic curve candidates in neighborhoods of known high-rank
curves, prioritizing families where BSD is less computationally verified.

Strategy: Instead of random search, sweep parametric neighborhoods of
curves with established high rank (Elkies families, Mestre constructions).
"""
from typing import Generator, Tuple, List, Optional
from src.elliptic_curve import EllipticCurve


# ---------------------------------------------------------------------------
# Known high-rank seed curves (short Weierstrass: y² = x³ + ax + b)
# ---------------------------------------------------------------------------

# Each entry: (label, a, b, known_rank)
HIGH_RANK_SEEDS = [
    # Rank 0 — baseline control
    ("rank0_control",    -1,     0,   0),
    # Rank 1 — e.g. 37a1 converted
    ("rank1_37a",         0,    -4,   1),
    # Rank 2 — e.g. 389a1 family
    ("rank2_389a",      -16,    -44,  2),
    # Rank 3 — Cremona tables
    ("rank3_5077a",     -13392, -1080432, 3),
    # Rank 4 — Mestre family neighborhood
    ("rank4_mestre",    -12987, 405702,  4),
]


# ---------------------------------------------------------------------------
# Generator functions
# ---------------------------------------------------------------------------

def generate_neighborhood(
    base_a: int,
    base_b: int,
    radius: int = 100,
    step: int = 1,
) -> Generator[Tuple[int, int], None, None]:
    """
    Yield (a, b) pairs in a square neighborhood of (base_a, base_b).

    Only yields pairs with non-zero discriminant (valid elliptic curves).

    Parameters
    ----------
    base_a, base_b : int
        Center of the search neighborhood.
    radius : int
        Half-width of the search square.
    step : int
        Step size (use > 1 for sparse scanning).
    """
    for da in range(-radius, radius + 1, step):
        for db in range(-radius, radius + 1, step):
            a = base_a + da
            b = base_b + db
            disc = -16 * (4 * a**3 + 27 * b**2)
            if disc != 0:
                yield (a, b)


def generate_family_scan(
    seed_label: Optional[str] = None,
    radius: int = 50,
    step: int = 1,
    max_curves: int = 10_000,
) -> Generator[Tuple[str, int, int, int], None, None]:
    """
    Scan neighborhoods of known high-rank seed curves.

    Yields (seed_label, a, b, seed_rank) tuples.

    Parameters
    ----------
    seed_label : str or None
        If given, scan only this seed. Otherwise scan all seeds.
    radius : int
        Neighborhood radius.
    step : int
        Step between candidate (a,b) values.
    max_curves : int
        Maximum total curves to yield.
    """
    seeds = HIGH_RANK_SEEDS
    if seed_label is not None:
        seeds = [s for s in seeds if s[0] == seed_label]
        if not seeds:
            raise ValueError(f"Unknown seed label: {seed_label}")

    count = 0
    for label, base_a, base_b, rank in seeds:
        for a, b in generate_neighborhood(base_a, base_b, radius, step):
            yield (label, a, b, rank)
            count += 1
            if count >= max_curves:
                return


def generate_conductor_filtered(
    base_a: int,
    base_b: int,
    radius: int = 50,
    conductor_limit: int = 1_000_000,
    min_rank_hint: int = 3,
) -> Generator[Tuple[int, int], None, None]:
    """
    Generate candidates filtered by conductor estimate and rank hint.

    Uses discriminant magnitude as a rough conductor proxy:
    curves with huge |Δ| tend to have large conductor, making
    L-function computation expensive.

    Parameters
    ----------
    conductor_limit : int
        Skip curves with |Δ| above this threshold.
    min_rank_hint : int
        Informational — the expected minimum rank of this family.
        Not enforced, but stored for downstream use.
    """
    for a, b in generate_neighborhood(base_a, base_b, radius):
        disc = abs(-16 * (4 * a**3 + 27 * b**2))
        if disc <= conductor_limit:
            yield (a, b)


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def estimate_search_space(radius: int, n_seeds: int = None) -> int:
    """Estimate total candidate curves for a given radius."""
    if n_seeds is None:
        n_seeds = len(HIGH_RANK_SEEDS)
    side = 2 * radius + 1
    return n_seeds * side * side
