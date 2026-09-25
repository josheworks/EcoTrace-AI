"""Efficiency analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ecotrace.storage.models import RequestEvent


@dataclass
class EfficiencyReport:
    """Report on workload efficiency.

    Attributes:
        total_requests: Total number of requests analyzed.
        duplicate_count: Number of exact duplicate requests.
        estimated_wasted_tokens: Tokens spent on duplicate requests.
        efficiency_score: Score from 0.0 (wasteful) to 1.0 (efficient).
        recommendations: List of human-readable recommendations.
        details: Additional analysis details.
    """
    total_requests: int = 0
    duplicate_count: int = 0
    estimated_wasted_tokens: int = 0
    efficiency_score: float = 1.0
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class EfficiencyAnalyzer:
    """Analyzes overall AI workload efficiency.

    Combines signals from duplicate detection, token usage, and
    latency to produce an efficiency report. Detailed analysis
    algorithms will be implemented in a future phase.
    """

    def analyze(
        self,
        events: List[RequestEvent],
        duplicate_count: int = 0,
        wasted_tokens: int = 0,
    ) -> EfficiencyReport:
        """Produce an efficiency report.

        Args:
            events: List of RequestEvent objects.
            duplicate_count: Number of detected duplicates.
            wasted_tokens: Tokens estimated as wasted.

        Returns:
            An EfficiencyReport.
        """
        if not events:
            return EfficiencyReport()

        total = len(events)
        total_tokens = sum(e.total_tokens for e in events)

        # Simple efficiency score: ratio of unique to total requests
        unique = total - duplicate_count
        score = unique / total if total > 0 else 1.0

        recommendations: List[str] = []
        if duplicate_count > 0:
            recommendations.append(
                f"Cache results for {duplicate_count} duplicate request(s) "
                f"to save ~{wasted_tokens} tokens."
            )

        return EfficiencyReport(
            total_requests=total,
            duplicate_count=duplicate_count,
            estimated_wasted_tokens=wasted_tokens,
            efficiency_score=round(score, 4),
            recommendations=recommendations,
            details={
                "total_tokens": total_tokens,
                "unique_requests": unique,
            },
        )
