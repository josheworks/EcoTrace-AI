"""Core optimizer module.

Orchestrates optimization strategies, generates recommendations, calculates estimated savings,
and simulates hypothetical optimized workloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ecotrace.analysis.duplicates import DuplicateAnalysisResult, DuplicateDetector
from ecotrace.analysis.latency import LatencyAnalyzer, LatencyStats
from ecotrace.analysis.similarity import (
    BasicSimilarityAnalyzer,
    SimilarityAnalysisResult,
    SimilarityAnalyzer,
)
from ecotrace.analysis.tokens import TokenAnalyzer, TokenStats
from ecotrace.impact.cost import CostCalculator
from ecotrace.optimization.recommendations import Recommendation, RecommendationEngine
from ecotrace.optimization.strategies import (
    ContextReductionStrategy,
    ExactCachingStrategy,
    HighLatencyStrategy,
    ModelRightSizingStrategy,
    OptimizationStrategy,
    SemanticCachingStrategy,
)
from ecotrace.storage.models import RequestEvent


@dataclass
class SavingsEstimate:
    """Quantified impact of observed waste and potential optimization opportunities.

    Exact duplicate savings are confirmed. Semantic savings are potential only.
    """
    exact_requests_avoided: int = 0
    semantic_requests_avoidable: int = 0
    requests_avoided: int = 0
    exact_tokens_avoided: int = 0
    semantic_tokens_avoidable: int = 0
    tokens_avoided: int = 0
    total_potential_tokens_avoided: int = 0
    input_tokens_avoided: int = 0
    output_tokens_avoided: int = 0
    estimated_cost_saved_usd: Optional[float] = None
    latency_improvement_potential_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "exact_requests_avoided": self.exact_requests_avoided,
            "semantic_requests_avoidable": self.semantic_requests_avoidable,
            "requests_avoided": self.requests_avoided,
            "exact_tokens_avoided": self.exact_tokens_avoided,
            "semantic_tokens_avoidable": self.semantic_tokens_avoidable,
            "tokens_avoided": self.tokens_avoided,
            "total_potential_tokens_avoided": self.total_potential_tokens_avoided,
            "input_tokens_avoided": self.input_tokens_avoided,
            "output_tokens_avoided": self.output_tokens_avoided,
            "estimated_cost_saved_usd": (
                round(self.estimated_cost_saved_usd, 6)
                if self.estimated_cost_saved_usd is not None
                else None
            ),
            "latency_improvement_potential_ms": (
                round(self.latency_improvement_potential_ms, 2)
                if self.latency_improvement_potential_ms is not None
                else None
            ),
            "details": self.details,
        }


@dataclass
class OptimizationSimulation:
    """Hypothetical simulation of workload optimization (BEFORE vs AFTER).

    This separates confirmed savings from potential savings and explains the assumptions.
    """
    original_requests: int = 0
    optimized_requests: int = 0
    requests_avoided: int = 0
    request_reduction_percent: float = 0.0
    original_tokens: int = 0
    optimized_tokens: int = 0
    tokens_avoided: int = 0
    token_reduction_percent: float = 0.0
    estimated_cost_saved_usd: Optional[float] = None
    assumptions: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "original_requests": self.original_requests,
            "optimized_requests": self.optimized_requests,
            "requests_avoided": self.requests_avoided,
            "request_reduction_percent": round(self.request_reduction_percent, 2),
            "original_tokens": self.original_tokens,
            "optimized_tokens": self.optimized_tokens,
            "tokens_avoided": self.tokens_avoided,
            "token_reduction_percent": round(self.token_reduction_percent, 2),
            "estimated_cost_saved_usd": (
                round(self.estimated_cost_saved_usd, 6)
                if self.estimated_cost_saved_usd is not None
                else None
            ),
            "assumptions": self.assumptions,
            "details": self.details,
        }


@dataclass
class OptimizationReport:
    """Full optimization report.

    Attributes:
        recommendations: List of applicable recommendations.
        total_events_analyzed: Number of events analyzed.
        savings: SavingsEstimate object.
        simulation: OptimizationSimulation object.
        metadata: Additional report metadata.
    """
    recommendations: List[Recommendation] = field(default_factory=list)
    total_events_analyzed: int = 0
    savings: SavingsEstimate = field(default_factory=SavingsEstimate)
    simulation: OptimizationSimulation = field(default_factory=OptimizationSimulation)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "total_events_analyzed": self.total_events_analyzed,
            "savings": self.savings.to_dict(),
            "simulation": self.simulation.to_dict(),
            "metadata": self.metadata,
        }


class Optimizer:
    """High-level optimization engine.

    Orchestrates strategies, calculates estimated savings, and simulates hypothetical optimization.
    """

    def __init__(
        self,
        strategies: Optional[List[OptimizationStrategy]] = None,
        cost_calculator: Optional[CostCalculator] = None,
    ) -> None:
        if strategies is None:
            strategies = [
                ExactCachingStrategy(),
                SemanticCachingStrategy(),
                ContextReductionStrategy(),
                ModelRightSizingStrategy(),
                HighLatencyStrategy(),
            ]
        self._engine = RecommendationEngine(strategies=strategies)
        self._cost_calculator = cost_calculator or CostCalculator()

    def optimize(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> OptimizationReport:
        """Run all optimization strategies and produce an optimization report."""
        if not events:
            return OptimizationReport()

        recommendations = self._engine.generate(
            events=events,
            duplicates=duplicates,
            similarity=similarity,
            tokens=tokens,
            latency=latency,
        )

        savings = self.estimate_savings(
            events=events,
            duplicates=duplicates,
            similarity=similarity,
            tokens=tokens,
            latency=latency,
        )

        sim = self.simulate(
            events=events,
            duplicates=duplicates,
            similarity=similarity,
            tokens=tokens,
        )

        return OptimizationReport(
            recommendations=recommendations,
            total_events_analyzed=len(events),
            savings=savings,
            simulation=sim,
        )

    def estimate_savings(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> SavingsEstimate:
        """Quantify confirmed exact-duplicate savings and potential semantic savings."""
        if not events:
            return SavingsEstimate()

        dup_res = duplicates or DuplicateDetector().analyze(events)
        if similarity is None:
            similarity = BasicSimilarityAnalyzer().analyze_corpus(
                events, exclude_ids=dup_res.duplicate_event_ids
            )
        tok_res = tokens or TokenAnalyzer().analyze(
            events, duplicate_result=dup_res, similarity_result=similarity
        )
        lat_res = latency or LatencyAnalyzer().analyze(events)

        exact_requests_avoided = dup_res.duplicate_count
        exact_tokens_avoided = dup_res.wasted_total_tokens
        exact_input_tokens_avoided = dup_res.wasted_input_tokens
        exact_output_tokens_avoided = dup_res.wasted_output_tokens

        semantic_requests_avoidable = (
            similarity.similar_pair_count if similarity else 0
        )
        semantic_tokens_avoidable = (
            similarity.potential_redundant_tokens if similarity else 0
        )
        total_potential_tokens_avoided = exact_tokens_avoided + semantic_tokens_avoidable

        total_requests_avoided = exact_requests_avoided
        total_tokens_avoided = exact_tokens_avoided

        cost_saved: Optional[float] = None
        if self._cost_calculator and dup_res.duplicate_event_ids:
            dup_events = [e for e in events if e.request_id in dup_res.duplicate_event_ids]
            cost_est = self._cost_calculator.estimate(dup_events)
            cost_saved = cost_est.total_cost_usd

        lat_imp: Optional[float] = None
        if lat_res.p95_latency_ms > 2000.0:
            lat_imp = lat_res.p95_latency_ms - 1500.0

        return SavingsEstimate(
            exact_requests_avoided=exact_requests_avoided,
            semantic_requests_avoidable=semantic_requests_avoidable,
            requests_avoided=total_requests_avoided,
            exact_tokens_avoided=exact_tokens_avoided,
            semantic_tokens_avoidable=semantic_tokens_avoidable,
            tokens_avoided=total_tokens_avoided,
            total_potential_tokens_avoided=total_potential_tokens_avoided,
            input_tokens_avoided=exact_input_tokens_avoided,
            output_tokens_avoided=exact_output_tokens_avoided,
            estimated_cost_saved_usd=cost_saved,
            latency_improvement_potential_ms=lat_imp,
            details={
                "source": "exact duplicates confirmed; semantic redundancy is potential only",
                "duplicate_event_ids": sorted(dup_res.duplicate_event_ids),
                "semantic_pair_count": semantic_requests_avoidable,
                "token_analysis": tok_res.to_dict() if tok_res else {},
                "latency_assumption": "p95 > 2000 ms suggests possible latency reduction from caching/context reduction",
            },
        )

    def simulate(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
    ) -> OptimizationSimulation:
        """Simulate a hypothetical optimized workload comparing BEFORE vs AFTER."""
        if not events:
            return OptimizationSimulation()

        orig_requests = len(events)
        orig_tokens = tokens.total_tokens if tokens else sum(e.total_tokens for e in events)
        dup_res = duplicates or DuplicateDetector().analyze(events)
        sim_res = similarity

        exact_requests_avoided = dup_res.duplicate_count
        exact_tokens_avoided = dup_res.wasted_total_tokens
        semantic_requests_avoidable = sim_res.similar_pair_count if sim_res else 0
        semantic_tokens_avoidable = sim_res.potential_redundant_tokens if sim_res else 0

        requests_avoided = exact_requests_avoided
        tokens_avoided = exact_tokens_avoided
        optimized_requests = max(0, orig_requests - requests_avoided)
        optimized_tokens = max(0, orig_tokens - tokens_avoided)

        request_reduction_percent = (
            (requests_avoided / orig_requests) * 100.0 if orig_requests > 0 else 0.0
        )
        token_reduction_percent = (
            (tokens_avoided / orig_tokens) * 100.0 if orig_tokens > 0 else 0.0
        )

        return OptimizationSimulation(
            original_requests=orig_requests,
            optimized_requests=optimized_requests,
            requests_avoided=requests_avoided,
            request_reduction_percent=request_reduction_percent,
            original_tokens=orig_tokens,
            optimized_tokens=optimized_tokens,
            tokens_avoided=tokens_avoided,
            token_reduction_percent=token_reduction_percent,
            estimated_cost_saved_usd=None,
            assumptions={
                "confirmed_savings": "Only exact duplicates are treated as guaranteed avoided requests/tokens.",
                "potential_savings": "Semantic redundancies are listed separately and not treated as guaranteed avoided work.",
                "formula": "optimized_requests = original_requests - exact_requests_avoided; optimized_tokens = original_tokens - exact_tokens_avoided",
            },
            details={
                "assumptions": {
                    "confirmed_savings": "Only exact duplicates are treated as guaranteed avoided requests/tokens.",
                    "potential_savings": "Semantic redundancies are listed separately and not treated as guaranteed avoided work.",
                    "formula": "optimized_requests = original_requests - exact_requests_avoided; optimized_tokens = original_tokens - exact_tokens_avoided",
                },
                "exact_requests_avoided": exact_requests_avoided,
                "semantic_requests_avoidable": semantic_requests_avoidable,
                "semantic_tokens_avoidable": semantic_tokens_avoidable,
                "potential_total_tokens_avoided": exact_tokens_avoided + semantic_tokens_avoidable,
            },
        )
