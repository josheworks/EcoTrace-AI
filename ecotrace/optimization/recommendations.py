"""Recommendation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ecotrace.optimization.strategies import OptimizationStrategy, StrategyResult
from ecotrace.storage.models import RequestEvent


@dataclass
class Recommendation:
    """A single optimization recommendation.

    Attributes:
        strategy: Name of the strategy.
        priority: Priority level ('high', 'medium', 'low').
        description: Human-readable description.
        estimated_savings: Estimated savings dict.
    """
    strategy: str = ""
    priority: str = "low"
    description: str = ""
    estimated_savings: Dict[str, Any] = field(default_factory=dict)


class RecommendationEngine:
    """Generates optimization recommendations by running strategies."""

    def __init__(
        self, strategies: List[OptimizationStrategy] | None = None
    ) -> None:
        self._strategies = strategies or []

    def add_strategy(self, strategy: OptimizationStrategy) -> None:
        """Register an optimization strategy."""
        self._strategies.append(strategy)

    def generate(
        self, events: List[RequestEvent]
    ) -> List[Recommendation]:
        """Run all strategies and return applicable recommendations.

        Args:
            events: Events to analyze.

        Returns:
            List of Recommendation objects.
        """
        recommendations: List[Recommendation] = []

        for strategy in self._strategies:
            result = strategy.evaluate(events)
            if result.applicable:
                recommendations.append(
                    Recommendation(
                        strategy=result.strategy_name,
                        priority=self._determine_priority(result),
                        description=result.recommendation,
                        estimated_savings=result.estimated_savings,
                    )
                )

        return recommendations

    @staticmethod
    def _determine_priority(result: StrategyResult) -> str:
        """Determine recommendation priority based on savings."""
        tokens_saved = result.estimated_savings.get("tokens", 0)
        if tokens_saved > 10000:
            return "high"
        if tokens_saved > 1000:
            return "medium"
        return "low"
