"""
BSD Falsifier -- Orchestrator for the Birch and Swinnerton-Dyer
falsifiability search.

Pipeline:
  1. Generate candidate curves (from parametric families)
  2. Compute algebraic rank bounds (point search)
  3. Compute analytic rank (L-function at s=1)
  4. Compare → flag ANOMALY if ranks disagree
  5. Record all results to evidence + experiment memory

Any ANOMALY requires independent verification before claim.
"""
import json
import time
from pathlib import Path
from typing import List, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime

from src.elliptic_curve import EllipticCurve
from src.candidate_generator import (
    generate_family_scan,
    HIGH_RANK_SEEDS,
)
from src.rank_estimator import RankEstimator, RankVerdict
from src.experiment_memory import ExperimentMemory


# ---------------------------------------------------------------------------
# Campaign configuration
# ---------------------------------------------------------------------------

@dataclass
class CampaignConfig:
    """Configuration for a falsifiability search campaign."""
    name: str = "bsd_default"
    seed_labels: Optional[List[str]] = None  # None = all seeds
    neighborhood_radius: int = 20
    step: int = 1
    max_curves: int = 1000
    prime_bound: int = 2000
    precision: int = 30
    height_bound: int = 50
    evidence_dir: str = "evidence"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "seed_labels": self.seed_labels,
            "neighborhood_radius": self.neighborhood_radius,
            "step": self.step,
            "max_curves": self.max_curves,
            "prime_bound": self.prime_bound,
            "precision": self.precision,
            "height_bound": self.height_bound,
        }


# ---------------------------------------------------------------------------
# Campaign results
# ---------------------------------------------------------------------------

@dataclass
class CampaignResult:
    """Aggregated results of a falsifiability campaign."""
    config: CampaignConfig
    total_curves: int = 0
    consistent: int = 0
    anomalies: int = 0
    inconclusive: int = 0
    errors: int = 0
    anomaly_details: List[dict] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def summary(self) -> str:
        lines = [
            f"# BSD Falsifiability Campaign: {self.config.name}",
            f"",
            f"> Completed: {datetime.utcnow().isoformat()}Z",
            f"> Elapsed: {self.elapsed_seconds:.1f}s",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Count |",
            f"|:---|---:|",
            f"| Total curves | {self.total_curves} |",
            f"| CONSISTENT | {self.consistent} |",
            f"| ANOMALY | {self.anomalies} |",
            f"| INCONCLUSIVE | {self.inconclusive} |",
            f"| Errors | {self.errors} |",
            f"",
        ]
        if self.anomaly_details:
            lines.append("## Anomalies Detected\n")
            for i, a in enumerate(self.anomaly_details, 1):
                lines.append(f"### Anomaly {i}: E(a={a['curve']['a']}, b={a['curve']['b']})")
                lines.append(f"- **Algebraic rank**: [{a['algebraic_rank_lower']}, {a.get('algebraic_rank_upper', '?')}]")
                lines.append(f"- **Analytic rank**: {a['analytic_rank']}")
                lines.append(f"- **Confidence**: {a['confidence']:.2f}")
                lines.append(f"- **Details**: {a['details']}")
                lines.append("")
        else:
            lines.append("## Result\n")
            lines.append("No anomalies detected. BSD consistent across all tested curves.\n")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Falsifier engine
# ---------------------------------------------------------------------------

class BSDFalsifier:
    """
    Orchestrator for BSD falsifiability search campaigns.

    Usage
    -----
    >>> falsifier = BSDFalsifier(working_dir=".")
    >>> config = CampaignConfig(name="test", max_curves=100)
    >>> result = falsifier.run(config)
    >>> print(result.summary())
    """

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.memory = ExperimentMemory(working_dir)

    def run(
        self,
        config: CampaignConfig,
        verbose: bool = False,
    ) -> CampaignResult:
        """
        Execute a falsifiability search campaign.

        Parameters
        ----------
        config : CampaignConfig
            Campaign parameters.
        verbose : bool
            Print progress to stdout.
        """
        result = CampaignResult(config=config)
        estimator = RankEstimator(
            prime_bound=config.prime_bound,
            precision=config.precision,
            height_bound=config.height_bound,
        )
        evidence_dir = self.working_dir / config.evidence_dir
        evidence_dir.mkdir(exist_ok=True)

        start_time = time.time()

        # Generate candidate stream
        seeds = config.seed_labels
        candidates = generate_family_scan(
            seed_label=seeds[0] if seeds and len(seeds) == 1 else None,
            radius=config.neighborhood_radius,
            step=config.step,
            max_curves=config.max_curves,
        )

        for i, (label, a, b, seed_rank) in enumerate(candidates):
            result.total_curves += 1
            try:
                verdict = estimator.analyze(a, b)

                if verdict.verdict == "CONSISTENT":
                    result.consistent += 1
                elif verdict.verdict == "ANOMALY":
                    result.anomalies += 1
                    result.anomaly_details.append(verdict.to_dict())
                    # Immediately save anomaly to evidence
                    self._save_anomaly(evidence_dir, verdict, i)
                else:
                    result.inconclusive += 1

                # Save to memory
                self.memory.save_experiment(
                    a=a, b=b,
                    seed_label=label,
                    analytic_rank=verdict.analytic_rank,
                    algebraic_lower=verdict.algebraic.lower,
                    algebraic_upper=verdict.algebraic.upper,
                    verdict=verdict.verdict,
                    confidence=verdict.confidence,
                )

                if verbose and (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    print(
                        f"  [{i+1}/{config.max_curves}] "
                        f"{verdict.verdict} | "
                        f"rate={rate:.1f} curves/s | "
                        f"anomalies={result.anomalies}"
                    )

            except (ValueError, ZeroDivisionError, OverflowError) as e:
                result.errors += 1
                if verbose:
                    print(f"  [{i+1}] ERROR on ({a},{b}): {e}")

        result.elapsed_seconds = time.time() - start_time

        # Save campaign report
        report_path = evidence_dir / f"campaign_{config.name}.md"
        report_path.write_text(result.summary(), encoding="utf-8")

        # Save machine-readable results
        json_path = evidence_dir / f"campaign_{config.name}.json"
        json_path.write_text(
            json.dumps({
                "config": config.to_dict(),
                "total": result.total_curves,
                "consistent": result.consistent,
                "anomalies": result.anomalies,
                "inconclusive": result.inconclusive,
                "errors": result.errors,
                "anomaly_details": result.anomaly_details,
                "elapsed_seconds": result.elapsed_seconds,
            }, indent=2),
            encoding="utf-8",
        )

        return result

    def _save_anomaly(
        self,
        evidence_dir: Path,
        verdict: RankVerdict,
        index: int,
    ) -> None:
        """Save individual anomaly to evidence/ for independent review."""
        filename = f"anomaly_{verdict.curve_a}_{verdict.curve_b}.json"
        filepath = evidence_dir / filename
        filepath.write_text(
            json.dumps(verdict.to_dict(), indent=2),
            encoding="utf-8",
        )

    def evaluate_single(self, a: int, b: int, verbose: bool = False) -> RankVerdict:
        """
        Evaluate a single curve.  Convenience method for quick inspection.
        """
        estimator = RankEstimator(
            prime_bound=2000,
            precision=30,
            height_bound=50,
        )
        verdict = estimator.analyze(a, b)
        if verbose:
            print(f"Curve: y² = x³ + {a}x + {b}")
            print(f"Algebraic rank: {verdict.algebraic}")
            print(f"Analytic rank: {verdict.analytic_rank}")
            print(f"L(E,1) = {verdict.L_values.get(0, '?')}")
            print(f"Verdict: {verdict.verdict} (confidence: {verdict.confidence:.2f})")
            print(f"Details: {verdict.details}")
        return verdict
