"""Optimization strategies module.

Contains data-driven optimization strategies that analyze workload patterns and generate
actionable recommendations for caching, context reduction, model right-sizing, and latency reduction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ecotrace.analysis.duplicates import DuplicateAnalysisResult, DuplicateDetector
from ecotrace.analysis.latency import LatencyAnalyzer, LatencyStats
from ecotrace.analysis.similarity import SimilarityAnalysisResult, SimilarityAnalyzer
from ecotrace.analysis.tokens import TokenAnalyzer, TokenStats
from ecotrace.storage.models import RequestEvent


@dataclass
class StrategyResult:
    """Result from evaluating an optimization strategy.

    Attributes:
        strategy_name: Identifier of the strategy.
        applicable: Whether the strategy generated a recommendation.
        recommendation: Human-readable recommendation string.
        priority: Priority level ('high', 'medium', 'low').
        estimated_savings: Dictionary of estimated savings (requests, tokens, cost, etc.).
        details: Additional context details.
    """
    strategy_name: str = ""
    applicable: bool = False
    recommendation: str = ""
    priority: str = "low"
    estimated_savings: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "applicable": self.applicable,
            "recommendation": self.recommendation,
            "priority": self.priority,
            "estimated_savings": self.estimated_savings,
            "details": self.details,
        }


class OptimizationStrategy(ABC):
    """Abstract base class for all optimization strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return unique strategy name."""
        ...

    @abstractmethod
    def evaluate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> StrategyResult:
        """Evaluate strategy against workload events and metrics."""
        ...


class ExactCachingStrategy(OptimizationStrategy):
    """Recommends exact-match response caching for duplicate prompts."""

    @property
    def name(self) -> str:
        return "exact_caching"

    def evaluate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> StrategyResult:
        if not events:
            return StrategyResult(strategy_name=self.name)

        dup_res = duplicates or DuplicateDetector().analyze(events)

        if dup_res.duplicate_count == 0:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="No exact duplicate requests detected.",
            )

        avoidable_requests = dup_res.duplicate_count
        avoidable_tokens = dup_res.wasted_total_tokens

        priority = "high" if avoidable_tokens > 5000 or avoidable_requests >= 5 else "medium"

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority=priority,
            recommendation=(
                f"Enable exact-response caching for repeated prompts. "
                f"Can eliminate {avoidable_requests} duplicate request(s) and save ~{avoidable_tokens} tokens."
            ),
            estimated_savings={
                "requests_avoided": avoidable_requests,
                "tokens_avoided": avoidable_tokens,
            },
            details={"duplicate_groups_count": len(dup_res.duplicate_groups)},
        )


class SemanticCachingStrategy(OptimizationStrategy):
    """Recommends semantic caching or prompt normalization for similar prompts."""

    @property
    def name(self) -> str:
        return "semantic_caching"

    def evaluate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> StrategyResult:
        if not events or len(events) < 2:
            return StrategyResult(strategy_name=self.name)

        sim_res = similarity
        if sim_res is None:
            from ecotrace.analysis.similarity import BasicSimilarityAnalyzer
            sim_res = BasicSimilarityAnalyzer().analyze_corpus(events)

        if sim_res.similar_pair_count == 0:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="No semantically redundant requests detected.",
            )

        similar_count = sim_res.similar_pair_count
        potential_tokens = sim_res.potential_redundant_tokens

        priority = "medium" if similar_count >= 3 else "low"

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority=priority,
            recommendation=(
                f"Consider semantic caching or prompt normalization. "
                f"Detected {similar_count} semantically similar request pair(s) "
                f"accounting for ~{potential_tokens} potentially redundant tokens."
            ),
            estimated_savings={
                "potential_requests_avoided": similar_count,
                "potential_tokens_avoided": potential_tokens,
            },
            details={"method_used": sim_res.method_used},
        )


class ContextReductionStrategy(OptimizationStrategy):
    """Recommends trimming context when large or repeated inputs create a potential reduction opportunity."""

    def __init__(
        self,
        high_token_threshold: int = 1500,
        repetition_threshold: float = 0.5,
    ) -> None:
        self.threshold = high_token_threshold
        self.repetition_threshold = repetition_threshold

    @property
    def name(self) -> str:
        return "context_reduction"

    def evaluate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> StrategyResult:
        if not events:
            return StrategyResult(strategy_name=self.name)

        high_context_events = [e for e in events if e.input_tokens >= self.threshold]
        if not high_context_events:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="Input context sizes are within normal bounds.",
            )

        count = len(high_context_events)
        average_input_tokens = sum(e.input_tokens for e in high_context_events) / count
        max_input_tokens = max(e.input_tokens for e in high_context_events)
        potential_context_tokens_saved = int(sum(e.input_tokens for e in high_context_events) * 0.2)

        recommendation = (
            f"Potentially reducible context detected in {count} request(s): average input tokens {average_input_tokens:.0f}, "
            f"max input tokens {max_input_tokens}. Large input prompts and repeated context are spending tokens on history that may be trimmed. "
            f"Consider summarization, prompt condensation, or history truncation. Potentially reducible context: ~{potential_context_tokens_saved} tokens."
        )

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority="medium" if count >= 2 else "low",
            recommendation=recommendation,
            estimated_savings={
                "potential_context_tokens_saved": potential_context_tokens_saved,
                "potential_tokens_avoided": potential_context_tokens_saved,
            },
            details={
                "average_input_tokens": round(average_input_tokens, 2),
                "max_input_tokens": max_input_tokens,
                "large_context_request_count": count,
                "potential_context_tokens_saved": potential_context_tokens_saved,
                "threshold_input_tokens": self.threshold,
                "assumption": "Large input + repeated/similar context + high token consumption indicates a potential context reduction opportunity, not guaranteed unnecessary context.",
            },
        )


class ModelRightSizingStrategy(OptimizationStrategy):
    """Only recommends model evaluation when the workload signals suggest a smaller model may fit."""

    def __init__(
        self,
        avg_tokens_threshold: int = 600,
        output_tokens_threshold: int = 150,
        max_input_tokens_threshold: int = 2000,
    ) -> None:
        self.avg_tokens_threshold = avg_tokens_threshold
        self.output_tokens_threshold = output_tokens_threshold
        self.max_input_tokens_threshold = max_input_tokens_threshold

    @property
    def name(self) -> str:
        return "model_rightsizing"

    def evaluate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> StrategyResult:
        if not events:
            return StrategyResult(strategy_name=self.name)

        large_model_events = []
        for e in events:
            model_lower = str(e.model).lower()
            if any(tag in model_lower for tag in ("gpt-4", "gpt-4o", "gemini-1.5-pro", "claude-3-opus")):
                if e.output_tokens <= self.output_tokens_threshold and e.input_tokens <= self.max_input_tokens_threshold:
                    large_model_events.append(e)

        if not large_model_events:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="No clear model right-sizing opportunity detected from the current workload characteristics.",
            )

        avg_tokens = sum(e.total_tokens for e in large_model_events) / len(large_model_events)
        candidates = [e.request_id for e in large_model_events[:5]]

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority="medium" if avg_tokens < self.avg_tokens_threshold else "low",
            recommendation=(
                "Model right-sizing opportunity detected. The workload contains relatively small and low-complexity requests "
                "using a larger model. Consider evaluating a smaller model for this workload. Potential impact: lower API cost, "
                "potentially lower latency, and lower compute usage."
            ),
            estimated_savings={"eligible_requests": len(large_model_events), "avg_tokens_per_request": round(avg_tokens, 2)},
            details={
                "candidate_request_ids": candidates,
                "average_tokens": round(avg_tokens, 2),
                "output_tokens_threshold": self.output_tokens_threshold,
                "max_input_tokens_threshold": self.max_input_tokens_threshold,
                "assumption": "This recommendation is explanatory and does not claim a smaller model is definitively equivalent without additional benchmark evidence.",
            },
        )


class HighLatencyStrategy(OptimizationStrategy):
    """Recommends optimization when p95 latency exceeds a configurable threshold."""

    def __init__(self, latency_threshold_ms: float = 1500.0) -> None:
        self.threshold = latency_threshold_ms

    @property
    def name(self) -> str:
        return "high_latency"

    def evaluate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> StrategyResult:
        if not events:
            return StrategyResult(strategy_name=self.name)

        lat = latency or LatencyAnalyzer().analyze(events)

        if lat.p95_latency_ms <= self.threshold:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="Workload latency is within the configured threshold.",
            )

        potential_reduction_ms = max(0.0, lat.p95_latency_ms - self.threshold)

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority="high" if lat.p95_latency_ms > (self.threshold * 1.5) else "medium",
            recommendation=(
                f"P95 latency: {lat.p95_latency_ms:.0f} ms. Threshold: {self.threshold:.0f} ms. "
                f"Recommendation: investigate caching, prompt/context reduction, batching, or model right-sizing. "
                f"EcoTrace is identifying a latency pattern; it does not know the exact root cause from this signal alone."
            ),
            estimated_savings={"latency_improvement_potential_ms": round(potential_reduction_ms, 1)},
            details={
                "p95_latency_ms": lat.p95_latency_ms,
                "threshold_ms": self.threshold,
                "evidence": "p95 latency above configured threshold",
            },
        )


# Backward compatibility aliases
CachingStrategy = ExactCachingStrategy
ModelDowngradeStrategy = ModelRightSizingStrategy
