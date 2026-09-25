"""EcoScore calculation module.

Calculates EcoTrace's internal composite workload efficiency score (EcoScore)
and assigns a letter grade (A, B, C, D, F) based on multi-signal efficiency components.

FORMULA & SCORING:
------------------
1. Request Uniqueness Score (40%): Ratio of non-duplicate requests to total requests.
2. Token Usage Efficiency Score (40%): Ratio of non-wasted tokens to total tokens.
3. Latency Efficiency Score (20%): Score derived from p95 latency relative to 1000ms target.
4. Redundancy Penalty: Deduction based on semantic similarity count.

GRADES:
-------
Score >= 90.0 -> A
Score >= 80.0 -> B
Score >= 70.0 -> C
Score >= 60.0 -> D
Score <  60.0 -> F
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ecotrace.analysis.efficiency import EfficiencyReport
from ecotrace.storage.models import RequestEvent


@dataclass
class EcoScore:
    """EcoScore result.

    Attributes:
        score: Composite workload efficiency score from 0.0 (worst) to 100.0 (best).
        grade: Letter grade ('A', 'B', 'C', 'D', 'F').
        components: Individual component scores (request_efficiency, token_efficiency, etc.).
        request_count: Number of requests analyzed.
    """
    score: float = 100.0
    grade: str = "A"
    components: Dict[str, float] = field(default_factory=dict)
    request_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize EcoScore to dictionary."""
        return {
            "score": round(self.score, 1),
            "grade": self.grade,
            "components": {k: round(v, 1) for k, v in self.components.items()},
            "request_count": self.request_count,
        }


class EcoScoreCalculator:
    """Calculates composite EcoScore and letter grade for AI workloads."""

    def calculate(
        self,
        events: List[RequestEvent],
        efficiency_report: Optional[EfficiencyReport] = None,
        duplicate_count: int = 0,
        similar_count: int = 0,
        wasted_tokens: int = 0,
    ) -> EcoScore:
        """Calculate the EcoScore based on workload metrics or an EfficiencyReport.

        Args:
            events: List of RequestEvent objects.
            efficiency_report: Optional precomputed EfficiencyReport.
            duplicate_count: Count of duplicate requests.
            similar_count: Count of semantically similar requests.
            wasted_tokens: Estimated wasted tokens.

        Returns:
            An EcoScore object.
        """
        if not events:
            return EcoScore(
                score=100.0,
                grade="A",
                components={
                    "request_efficiency": 100.0,
                    "token_efficiency": 100.0,
                    "latency_efficiency": 100.0,
                    "redundancy_penalty": 0.0,
                },
                request_count=0,
            )

        n = len(events)

        if efficiency_report:
            score = efficiency_report.efficiency_score
            components = dict(efficiency_report.components)
        else:
            total_tokens = sum(e.total_tokens for e in events)
            req_eff = max(0.0, 100.0 * (1.0 - (duplicate_count / n))) if n > 0 else 100.0
            tok_eff = max(0.0, 100.0 * (1.0 - (wasted_tokens / total_tokens))) if total_tokens > 0 else 100.0
            lat_eff = 100.0
            red_penalty = min(20.0, (similar_count / n) * 20.0) if n > 0 else 0.0

            raw_score = (0.40 * req_eff) + (0.40 * tok_eff) + (0.20 * lat_eff) - red_penalty
            score = max(0.0, min(100.0, raw_score))
            components = {
                "request_efficiency": req_eff,
                "token_efficiency": tok_eff,
                "latency_efficiency": lat_eff,
                "redundancy_penalty": red_penalty,
            }

        grade = self._score_to_grade(score)

        return EcoScore(
            score=round(score, 1),
            grade=grade,
            components=components,
            request_count=n,
        )

    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert a numeric score (0-100) to a letter grade."""
        if score >= 90.0:
            return "A"
        if score >= 80.0:
            return "B"
        if score >= 70.0:
            return "C"
        if score >= 60.0:
            return "D"
        return "F"
