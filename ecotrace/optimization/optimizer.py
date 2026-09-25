"""Core optimizer module.

Orchestrates optimization strategies, generates recommendations, calculates estimated savings,
and simulates hypothetical optimized workloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ecotrace.analysis.duplicates import DuplicateAnalysisResult, DuplicateDetector
from ecotrace.analysis.latency import LatencyAnalyzer, LatencyStats
from ecotrace.analysis.similarity import SimilarityAnalysisResult, SimilarityAnalyzer
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
    """Quantified impact of detected waste and optimization potential.

    Attributes:
        requests_avoided: Total requests that can be avoided via caching/deduplication.
        tokens_avoided: Total tokens saved by eliminating waste.
        input_tokens_avoided: Input tokens saved.
        output_tokens_avoided: Output tokens saved.
        estimated_cost_saved_usd: Estimated cost savings in USD (None if pricing unavailable).
        latency_improvement_potential_ms: Potential latency reduction in ms.
        details: Additional context details.
    """
    requests_avoided: int = 0
    tokens_avoided: int = 0
    input_tokens_avoided: int = 0
    output_tokens_avoided: int = 0
    estimated_cost_saved_usd: Optional[float] = None
    latency_improvement_potential_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "requests_avoided": self.requests_avoided,
            "tokens_avoided": self.tokens_avoided,
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

    Attributes:
        original_requests: Total requests in original workload.
        optimized_requests: Estimated requests after optimization.
        requests_avoided: Number of requests avoided.
        original_tokens: Total tokens in original workload.
        optimized_tokens: Estimated tokens after optimization.
        tokens_avoided: Total tokens saved.
        estimated_cost_saved_usd: Estimated financial savings in USD.
    """
    original_requests: int = 0
    optimized_requests: int = 0
    requests_avoided: int = 0
    original_tokens: int = 0
    optimized_tokens: int = 0
    tokens_avoided: int = 0
    estimated_cost_saved_usd: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "original_requests": self.original_requests,
            "optimized_requests": self.optimized_requests,
            "requests_avoided": self.requests_avoided,
            "original_tokens": self.original_tokens,
            "optimized_tokens": self.optimized_tokens,
            "tokens_avoided": self.tokens_avoided,
            "estimated_cost_saved_usd": (
                round(self.estimated_cost_saved_usd, 6)
                if self.estimated_cost_saved_usd is not None
                else None
            ),
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
        """Quantify potential savings from exact duplicates and semantic redundancy."""
        if not events:
            return SavingsEstimate()

        dup_res = duplicates or DuplicateDetector().analyze(events)
        tok_res = tokens or TokenAnalyzer().analyze(events, duplicate_result=dup_res)
        lat_res = latency or LatencyAnalyzer().analyze(events)

        requests_avoided = dup_res.duplicate_count
        dup_tokens_avoided = dup_res.wasted_total_tokens
        dup_in_avoided = dup_res.wasted_input_tokens
        dup_out_avoided = dup_res.wasted_output_tokens

        sim_tokens_avoided = similarity.potential_redundant_tokens if similarity else 0
        total_tokens_avoided = dup_tokens_avoided + sim_tokens_avoided

        # Cost estimation if pricing is available
        cost_saved: Optional[float] = None
        if self._cost_calculator and dup_res.duplicate_event_ids:
            dup_events = [e for e in events if e.request_id in dup_res.duplicate_event_ids]
            cost_est = self._cost_calculator.estimate(dup_events)
            cost_saved = cost_est.total_cost_usd

        lat_imp: Optional[float] = None
        if lat_res.p95_latency_ms > 2000.0:
            lat_imp = lat_res.p95_latency_ms - 1500.0

        return SavingsEstimate(
            requests_avoided=requests_avoided,
            tokens_avoided=total_tokens_avoided,
            input_tokens_avoided=dup_in_avoided,
            output_tokens_avoided=dup_out_avoided,
            estimated_cost_saved_usd=cost_saved,
            latency_improvement_potential_ms=lat_imp,
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

        savings = self.estimate_savings(
            events=events,
            duplicates=duplicates,
            similarity=similarity,
            tokens=tokens,
        )

        opt_requests = max(1, orig_requests - savings.requests_avoided)
        opt_tokens = max(0, orig_tokens - savings.tokens_avoided)

        return OptimizationSimulation(
            original_requests=orig_requests,
            optimized_requests=opt_requests,
            requests_avoided=savings.requests_avoided,
            original_tokens=orig_tokens,
            optimized_tokens=opt_tokens,
            tokens_avoided=savings.tokens_avoided,
            estimated_cost_saved_usd=savings.estimated_cost_saved_usd,
        )
