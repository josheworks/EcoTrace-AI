"""Core optimizer module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ecotrace.optimization.recommendations import Recommendation, RecommendationEngine
from ecotrace.optimization.strategies import (
    CachingStrategy,
    ModelDowngradeStrategy,
    OptimizationStrategy,
)
from ecotrace.storage.models import RequestEvent


@dataclass
class OptimizationReport:
    """Full optimization report.

    Attributes:
        recommendations: List of applicable recommendations.
        total_events_analyzed: Number of events analyzed.
        metadata: Additional report metadata.
    """
    recommendations: List[Recommendation] = field(default_factory=list)
    total_events_analyzed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Optimizer:
    """High-level optimization engine.

    Orchestrates strategies and produces an optimization report.
    """

    def __init__(
        self, strategies: List[OptimizationStrategy] | None = None
    ) -> None:
        if strategies is None:
            strategies = [CachingStrategy(), ModelDowngradeStrategy()]
        self._engine = RecommendationEngine(strategies=strategies)

    def optimize(self, events: List[RequestEvent]) -> OptimizationReport:
        """Run all optimization strategies and return a report.

        Args:
            events: Events to analyze.

        Returns:
            An OptimizationReport.
        """
        recommendations = self._engine.generate(events)
        return OptimizationReport(
            recommendations=recommendations,
            total_events_analyzed=len(events),
        )
