"""
Experiment Memory -- ReMe file-based persistence for BSD campaigns.

Tracks explored curve families, rank verdicts, anomalies,
and campaign results across sessions.

Pattern inherited from Yang-Mills experiment_memory.py.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional


class ExperimentMemory:
    """
    Persistent memory for BSD falsifiability experiments.
    Uses MEMORY.md and daily logs (ReMe CoPaw pattern).
    """

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.memory_file = self.working_dir / "MEMORY.md"
        self.memory_dir = self.working_dir / "memory"
        self.memory_dir.mkdir(exist_ok=True)

    def load_explored_curves(self) -> List[dict]:
        """Load already-explored curves from the daily logs."""
        explored = []
        if not self.memory_dir.exists():
            return explored
        for log_file in sorted(self.memory_dir.glob("*.jsonl")):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            explored.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return explored

    def save_experiment(
        self,
        a: int,
        b: int,
        seed_label: str,
        analytic_rank: int,
        algebraic_lower: int,
        algebraic_upper: Optional[int],
        verdict: str,
        confidence: float,
    ) -> None:
        """Save an experiment result to daily log and update MEMORY.md."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_log = self.memory_dir / f"{today}.jsonl"

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "curve": {"a": a, "b": b},
            "seed_label": seed_label,
            "analytic_rank": analytic_rank,
            "algebraic_lower": algebraic_lower,
            "algebraic_upper": algebraic_upper,
            "verdict": verdict,
            "confidence": confidence,
        }

        with open(daily_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Update summary
        self._update_memory(verdict)

    def _update_memory(self, latest_verdict: str) -> None:
        """Rewrite MEMORY.md with current stats."""
        # Count entries from all daily logs
        all_entries = self.load_explored_curves()
        n_total = len(all_entries)
        n_anomalies = sum(1 for e in all_entries if e.get("verdict") == "ANOMALY")
        n_consistent = sum(1 for e in all_entries if e.get("verdict") == "CONSISTENT")
        n_inconclusive = n_total - n_anomalies - n_consistent

        # Unique seeds explored
        seeds = set(e.get("seed_label", "?") for e in all_entries)

        lines = [
            "# BSD Experiment Memory\n\n",
            f"> Last updated: {datetime.utcnow().isoformat()}Z\n\n",
            "## Summary\n\n",
            f"- **Total curves evaluated**: {n_total}\n",
            f"- **CONSISTENT**: {n_consistent}\n",
            f"- **ANOMALY**: {n_anomalies}\n",
            f"- **INCONCLUSIVE**: {n_inconclusive}\n",
            f"- **Seed families explored**: {', '.join(sorted(seeds))}\n",
            f"- **Latest verdict**: {latest_verdict}\n",
        ]

        if n_anomalies > 0:
            lines.append("\n## ⚠️ Anomalies\n\n")
            for e in all_entries:
                if e.get("verdict") == "ANOMALY":
                    c = e.get("curve", {})
                    lines.append(
                        f"- `E(a={c.get('a')}, b={c.get('b')})` "
                        f"— rank_an={e.get('analytic_rank')}, "
                        f"rank_alg=[{e.get('algebraic_lower')}, "
                        f"{e.get('algebraic_upper', '?')}], "
                        f"conf={e.get('confidence', 0):.2f}\n"
                    )

        self.memory_file.write_text("".join(lines), encoding="utf-8")

    def get_stats(self) -> dict:
        """Return current experiment statistics."""
        entries = self.load_explored_curves()
        return {
            "total": len(entries),
            "anomalies": sum(1 for e in entries if e.get("verdict") == "ANOMALY"),
            "consistent": sum(1 for e in entries if e.get("verdict") == "CONSISTENT"),
            "inconclusive": sum(
                1 for e in entries
                if e.get("verdict") not in ("ANOMALY", "CONSISTENT")
            ),
        }
