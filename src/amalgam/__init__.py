"""
src/amalgam — Gahenax BSD Amalgam Architecture

A hybrid engine for elliptic curve BSD testing that combines:
  - SageMath 2-Selmer descent (exact algebraic rank)
  - C++ GMP/FLINT Euler product (fast arithmetic — stub provided)
  - Compatible with MPI, HTCondor, SLURM dispatch

Usage:
    from src.amalgam.bsd_worker import compute_bsd
    result = compute_bsd(a4=-94816050, a6=368541849450)
"""

from .bsd_worker import compute_bsd
from .sage_engine import rank_descent, sage_available

__all__ = ["compute_bsd", "rank_descent", "sage_available"]
__version__ = "1.0.0"
