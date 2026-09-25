"""Recommendation engine module.

Executes optimization strategies against workload metrics and outputs structured recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ecotrace.analysis.duplicates import DuplicateAnalysisResult
from ecotrace.analysis.latency import LatencyStats
from ecotrace.analysis.similarity import SimilarityAnalysisResult
from ecotrace.analysis.tokens import TokenStats
from ecotrace.optimization.strategies import OptimizationStrategy, StrategyResult
from ecotrace.storage.models import RequestEvent


@dataclass
class Recommendation:
    """A single optimization recommendation.

    Attributes:
        strategy: Name of the strategy.
        priority: Priority level ('high', 'medium', 'low').
        description: Human-readable description.
        estimated_savings: Dictionary of estimated savings.
        details: Extra context details.
    """
    strategy: str = ""
    priority: str = "low"
    description: str = ""
    estimated_savings: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "strategy": self.strategy,
            "priority": self.priority,
            "description": self.description,
            "estimated_savings": self.estimated_savings,
            "details": self.details,
        }


class RecommendationEngine:
    """Generates optimization recommendations by evaluating registered strategies."""

    def __init__(
        self, strategies: Optional[List[OptimizationStrategy]] = None
    ) -> None:
        self._strategies = strategies or []

    def add_strategy(self, strategy: OptimizationStrategy) -> None:
        """Register an optimization strategy."""
        self._strategies.append(strategy)

    def generate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> List[Recommendation]:
        """Run registered strategies and return applicable recommendations.

        Args:
            events: Events to analyze.
            duplicates: Result from DuplicateDetector.
            similarity: Result from SimilarityAnalyzer.
            tokens: Result from TokenAnalyzer.
            latency: Result from LatencyAnalyzer.

        Returns:
            List of Recommendation objects.
        """
        recommendations: List[Recommendation] = []

        for strategy in self._strategies:
            result = strategy.evaluate(
                events=events,
                duplicates=duplicates,
                similarity=similarity,
                tokens=tokens,
                latency=latency,
            )
            if result.applicable:
                recommendations.append(
                    Recommendation(
                        strategy=result.strategy_name,
                        priority=result.priority,
                        description=result.recommendation,
                        estimated_savings=result.estimated_savings,
                        details=result.details,
                    )
                )

        return recommendations
