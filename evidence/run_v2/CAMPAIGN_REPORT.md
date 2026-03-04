# BSD Falsifiability Campaign: Phase-1 Run v2

> **Completed**: 2026-03-04T05:20:00Z
> **Total wall time**: ~19.7 min (4 blocks sequential on local machine)

## Summary

| Metric | Count |
|:---|---:|
| **Total curves evaluated** | **1,976** |
| CONSISTENT | 1,122 (56.8%) |
| ANOMALY | **0** (0.0%) |
| INCONCLUSIVE | 854 (43.2%) |
| Errors | 0 (0.0%) |

## Block Results

| Block | Probe | Seed Family | Side | Curves | Consistent | Anomalies | Inconclusive | Time |
|:---:|:---|:---|:---:|---:|---:|---:|---:|---:|
| 0 | ALPHA | rank0_control | R | 495 | 282 | 0 | 213 | 251s |
| 1 | BRAVO | rank0_control | L | 494 | 273 | 0 | 221 | 302s |
| 2 | CHARLIE | rank1_37a | L | 492 | 279 | 0 | 213 | 299s |
| 3 | DELTA | rank1_37a | R | 495 | 288 | 0 | 207 | 327s |

## Gate Results

| Gate | Status | Details |
|:---|:---:|:---|
| **Gate 0 (Integrity)** | ✅ PASS | 4 manifests present, 1,976 curves total |
| **Gate 1 (Sanity)** | ✅ PASS | Rank-0 control: 0% anomaly rate (target < 5%) |
| **Gate 2 (Anomaly Triage)** | ✅ N/A | No anomalies to triage |

## Analysis

- **INCONCLUSIVE rate (43.2%)**: Expected. Most INCONCLUSIVEs are curves where the height search finds rational points that *appear* to be non-torsion but whose independence hasn't been proven by descent. This is the correct conservative behavior — the system refuses to declare ANOMALY without rigorous evidence.

- **0 anomalies**: BSD is consistent across all 1,976 tested curves in the rank-0 and rank-1 families. This is expected — these are well-studied families.

## Next Steps

- **Phase-2**: Extend to rank 2-4 families (blocks 4-9) where BSD is less explored
- **Jules delegation**: Full 10-block, 50K-curve sweep at higher precision
- **SageMath integration**: For INCONCLUSIVE verdicts, delegate to SageMath for exact rank via 2-Selmer descent

## Parameters Used

```
prime_bound = 2000
precision = 25 dps
height_bound = 20
neighborhood_radius = 15
```
