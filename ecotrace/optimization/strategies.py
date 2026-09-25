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
    """Recommends trimming chat history or summarizing large contexts."""

    def __init__(self, high_token_threshold: int = 1500) -> None:
        self.threshold = high_token_threshold

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
        total_input = sum(e.input_tokens for e in high_context_events)
        estimated_savable_tokens = int(total_input * 0.25)  # Estimate 25% savings from context pruning

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority="medium" if count >= 2 else "low",
            recommendation=(
                f"Large input context detected in {count} request(s) (>= {self.threshold} input tokens). "
                f"Consider removing unnecessary system context, summarizing chat history, or truncating history. "
                f"Estimated potential savings: ~{estimated_savable_tokens} input tokens."
            ),
            estimated_savings={"potential_tokens_avoided": estimated_savable_tokens},
            details={"high_context_request_count": count},
        )


class ModelRightSizingStrategy(OptimizationStrategy):
    """Recommends using smaller/cheaper models for simple, low-output workloads."""

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

        expensive_models = {"gpt-4", "gpt-4o", "gemini-1.5-pro", "claude-3-opus"}
        candidates = []

        for e in events:
            model_lower = str(e.model).lower()
            if any(exp in model_lower for exp in expensive_models):
                # Simple task heuristically identified by short output (< 150 tokens) and small prompt
                if e.output_tokens > 0 and e.output_tokens < 150:
                    candidates.append(e)

        if not candidates:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="No model right-sizing opportunities detected.",
            )

        count = len(candidates)
        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority="medium",
            recommendation=(
                f"Potential model right-sizing opportunity detected in {count} request(s). "
                f"High-capability models are being used for short-response queries. "
                f"Consider routing simpler queries to a smaller model (e.g., gpt-4o-mini, gemini-1.5-flash)."
            ),
            estimated_savings={"eligible_requests": count},
            details={"candidate_request_ids": [c.request_id for c in candidates[:5]]},
        )


class HighLatencyStrategy(OptimizationStrategy):
    """Recommends optimization for high p95 latency workloads."""

    def __init__(self, latency_threshold_ms: float = 2000.0) -> None:
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

        if lat.p95_latency_ms < self.threshold:
            return StrategyResult(
                strategy_name=self.name,
                applicable=False,
                recommendation="Workload latency is within acceptable limits.",
            )

        potential_reduction_ms = lat.p95_latency_ms - (self.threshold * 0.7)

        return StrategyResult(
            strategy_name=self.name,
            applicable=True,
            priority="high" if lat.p95_latency_ms > 4000.0 else "medium",
            recommendation=(
                f"High p95 latency detected ({lat.p95_latency_ms:.0f} ms > {self.threshold:.0f} ms). "
                f"Consider: using faster provider inference, shorter max tokens, response streaming, "
                f"or caching repeated queries."
            ),
            estimated_savings={"latency_improvement_potential_ms": round(potential_reduction_ms, 1)},
            details={"p95_latency_ms": lat.p95_latency_ms},
        )


# Backward compatibility aliases
CachingStrategy = ExactCachingStrategy
ModelDowngradeStrategy = ModelRightSizingStrategy
