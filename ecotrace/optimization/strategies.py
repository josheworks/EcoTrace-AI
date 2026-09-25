"""Optimization strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from ecotrace.storage.models import RequestEvent


@dataclass
class StrategyResult:
    """Result from applying an optimization strategy.

    Attributes:
        strategy_name: Name of the strategy that produced this result.
        applicable: Whether the strategy is applicable to the input.
        recommendation: Human-readable recommendation.
        estimated_savings: Estimated savings (tokens, cost, etc.).
        details: Additional details.
    """
    strategy_name: str = ""
    applicable: bool = False
    recommendation: str = ""
    estimated_savings: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


class OptimizationStrategy(ABC):
    """Abstract base class for optimization strategies.

    Each strategy examines a set of events and produces
    recommendations for reducing waste.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name."""
        ...

    @abstractmethod
    def evaluate(self, events: List[RequestEvent]) -> StrategyResult:
        """Evaluate the strategy against a list of events.

        Args:
            events: Events to analyze.

        Returns:
            StrategyResult with recommendations.
        """
        ...


class CachingStrategy(OptimizationStrategy):
    """Recommends caching for duplicate requests."""

    @property
    def name(self) -> str:
        return "caching"

    def evaluate(self, events: List[RequestEvent]) -> StrategyResult:
        """Evaluate caching opportunity."""
        if not events:
            return StrategyResult(strategy_name=self.name)

        # Count duplicate hashes
        hash_counts: Dict[str, int] = {}
        for e in events:
            if e.request_hash:
                hash_counts[e.request_hash] = hash_counts.get(e.request_hash, 0) + 1

        duplicates = {h: c for h, c in hash_counts.items() if c > 1}
        dup_count = sum(c - 1 for c in duplicates.values())

        if dup_count == 0:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="No duplicate requests detected.",
            )

        wasted = sum(
            e.total_tokens
            for e in events
            if e.request_hash in duplicates
        )

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            recommendation=(
                f"Implement response caching to eliminate {dup_count} "
                f"duplicate request(s) and save ~{wasted} tokens."
            ),
            estimated_savings={"duplicate_requests": dup_count, "tokens": wasted},
        )


class ModelDowngradeStrategy(OptimizationStrategy):
    """Recommends using smaller/cheaper models where possible.

    Placeholder: real implementation would analyze task complexity.
    """

    @property
    def name(self) -> str:
        return "model_downgrade"

    def evaluate(self, events: List[RequestEvent]) -> StrategyResult:
        """Placeholder evaluation."""
        # Future: analyze prompt complexity to determine if a smaller model suffices
        return StrategyResult(
            strategy_name=self.name,
            applicable=False,
            recommendation="Model downgrade analysis not yet implemented.",
        )
