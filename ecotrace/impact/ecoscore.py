"""EcoScore calculation.

The EcoScore is a composite metric combining efficiency, cost, energy,
and carbon impact into a single 0-100 score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ecotrace.storage.models import RequestEvent


@dataclass
class EcoScore:
    """EcoScore result.

    Attributes:
        score: Composite score from 0 (worst) to 100 (best).
        grade: Letter grade (A-F).
        components: Individual component scores.
        request_count: Number of requests analyzed.
    """
    score: float = 100.0
    grade: str = "A"
    components: Dict[str, float] = field(default_factory=dict)
    request_count: int = 0


class EcoScoreCalculator:
    """Calculates a composite EcoScore.

    The scoring algorithm will be refined in future phases.
    Currently provides a simple placeholder based on duplicate ratio.
    """

    def calculate(
        self,
        events: List[RequestEvent],
        duplicate_count: int = 0,
        total_cost_usd: float = 0.0,
        total_gco2: float = 0.0,
    ) -> EcoScore:
        """Calculate the EcoScore.

        Args:
            events: Events to score.
            duplicate_count: Number of duplicate requests.
            total_cost_usd: Estimated cost in USD.
            total_gco2: Estimated CO2 in grams.

        Returns:
            An EcoScore.
        """
        if not events:
            return EcoScore()

        n = len(events)

        # Efficiency component: penalize duplicates
        dup_ratio = duplicate_count / n if n > 0 else 0
        efficiency_score = max(0.0, 1.0 - dup_ratio) * 100

        # Placeholder components
        score = round(efficiency_score, 1)
        grade = self._score_to_grade(score)

        return EcoScore(
            score=score,
            grade=grade,
            components={
                "efficiency": round(efficiency_score, 1),
                "duplicate_ratio": round(dup_ratio, 4),
            },
            request_count=n,
        )

    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert a numeric score to a letter grade."""
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"
