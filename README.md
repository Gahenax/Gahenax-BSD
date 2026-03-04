# Gahenax-BSD — Birch & Swinnerton-Dyer Falsifiability Engine

> *Hunting counterexamples in the arithmetic of elliptic curves.*

## The Conjecture

The **Birch and Swinnerton-Dyer (BSD) conjecture** predicts that for an elliptic curve $E: y^2 = x^3 + ax + b$ over $\mathbb{Q}$:

$$\text{rank}(E(\mathbb{Q})) = \text{ord}_{s=1}\, L(E, s)$$

In plain language: the number of independent rational solutions of infinite order (**algebraic rank**) equals the order of vanishing of the curve's L-function at $s=1$ (**analytic rank**).

This is one of the seven Millennium Prize Problems ($1,000,000 USD).

## What This Lab Does

This is **not** a verification lab. This is a **falsifiability search engine**.

We systematically scan parametric neighborhoods of known high-rank elliptic curves, independently compute both sides of BSD, and flag any curve where:

$$\text{rank}_{\text{algebraic}} \neq \text{rank}_{\text{analytic}}$$

Any such discrepancy is a **candidate counterexample** or a **computational error**. Distinguishing both is the central challenge.

## Architecture

```
Candidate Generator     →  Parametric families near high-rank seeds
        ↓
Rational Point Search   →  Nagell-Lutz + height-bounded search → rank bounds
        ↓
L-function Engine       →  Euler product L(E,s) with mpmath precision
        ↓
Rank Estimator          →  Derivatives of L(E,s) at s=1 → analytic rank
        ↓
BSD Falsifier           →  Compare ranks → CONSISTENT / ANOMALY / INCONCLUSIVE
        ↓
Experiment Memory       →  Append-only JSONL ledger + MEMORY.md
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Evaluate a single curve: y² = x³ - x (rank 0)
python -c "
from src.bsd_falsifier import BSDFalsifier
f = BSDFalsifier()
f.evaluate_single(-1, 0, verbose=True)
"

# Run a small campaign
python -c "
from src.bsd_falsifier import BSDFalsifier, CampaignConfig
f = BSDFalsifier()
config = CampaignConfig(name='test', max_curves=50, neighborhood_radius=5)
result = f.run(config, verbose=True)
print(result.summary())
"
```

## Falsifiability Protocol

| Hypothesis | Failure Condition |
|:---|:---|
| **H0:** BSD holds for all $E/\mathbb{Q}$ | Find a curve where $r_{\text{alg}} \neq r_{\text{an}}$, confirmed by 2 independent systems |
| **H1:** Anomaly is numerical error | Same curve, same discrepancy in SageMath + Magma independently |
| **H2:** Search space is sufficient | No anomalies after 10M+ curves → extend to families of rank ≥ 5 |

> **Honest disclaimer:** BSD has been verified for millions of curves. A counterexample, if it exists, likely lives in high-rank families ($r \geq 4$) where computation is expensive and numerically unstable.

## Verification

```bash
set PYTHONPATH=.
pytest tests/test_bsd.py -v
```

## Repository Structure

```
Gahenax-BSD/
├── README.md
├── requirements.txt
├── src/
│   ├── elliptic_curve.py       ← Weierstrass model, point arithmetic, a_p
│   ├── candidate_generator.py  ← High-rank family neighborhoods
│   ├── rational_points.py      ← Nagell-Lutz, height search, rank bounds
│   ├── l_function.py           ← L(E,s) Euler product (mpmath)
│   ├── rank_estimator.py       ← Analytic rank via derivatives at s=1
│   ├── bsd_falsifier.py        ← Orchestrator + anomaly detector
│   └── experiment_memory.py    ← ReMe persistent memory
├── tests/
│   └── test_bsd.py
├── evidence/                   ← Campaign reports + anomaly JSONs
└── memory/                     ← Daily experiment logs (JSONL)
```

---

*Deterministic Truth Laboratory — Gahenax (2026)*
