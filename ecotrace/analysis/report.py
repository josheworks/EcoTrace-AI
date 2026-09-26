"""Unified workload report module.

Combines all analysis phases (duplicates, semantic similarity, tokens, latency,
efficiency, optimization recommendations, estimated savings, EcoScore, and resource impact)
into a single serializable WorkloadReport object.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ecotrace.analysis.duplicates import DuplicateAnalysisResult, DuplicateDetector
from ecotrace.analysis.efficiency import EfficiencyAnalyzer, EfficiencyReport
from ecotrace.analysis.latency import LatencyAnalyzer, LatencyStats
from ecotrace.analysis.similarity import (
    EmbeddingSimilarityAnalyzer,
    SimilarityAnalysisResult,
    SimilarityAnalyzer,
)
from ecotrace.analysis.tokens import TokenAnalyzer, TokenStats
from ecotrace.impact.carbon import CarbonEstimate, CarbonEstimator
from ecotrace.impact.ecoscore import EcoScore, EcoScoreCalculator
from ecotrace.impact.energy import EnergyEstimate, EnergyEstimator
from ecotrace.optimization.optimizer import (
    OptimizationReport,
    Optimizer,
    OptimizationSimulation,
    SavingsEstimate,
)
from ecotrace.storage.models import RequestEvent


@dataclass
class RequestMetrics:
    """Summary of raw request events.

    Attributes:
        total_requests: Total events processed.
        unique_providers: Number of distinct AI providers used.
        unique_models: Number of distinct models used.
        provider_breakdown: Count of requests per provider.
        model_breakdown: Count of requests per model.
    """
    total_requests: int = 0
    unique_providers: int = 0
    unique_models: int = 0
    provider_breakdown: Dict[str, int] = field(default_factory=dict)
    model_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "unique_providers": self.unique_providers,
            "unique_models": self.unique_models,
            "provider_breakdown": self.provider_breakdown,
            "model_breakdown": self.model_breakdown,
        }


@dataclass
class WorkloadReport:
    """Unified AI Workload Analysis and Optimization Report.

    Attributes:
        project: Optional project or session name.
        timestamp: Report creation timestamp (ISO format).
        request_metrics: Basic request volume and provider metrics.
        duplicates: Exact duplicate detection analysis result.
        similarity: Semantic similarity analysis result.
        tokens: Token consumption and waste analysis result.
        latency: Latency distribution statistics.
        efficiency: Multi-signal efficiency report.
        optimization: Recommended optimization strategies, savings, and simulation.
        ecoscore: Overall composite EcoScore and grade.
        energy_impact: Optional energy consumption proxy estimate.
        carbon_impact: Optional carbon footprint proxy estimate.
    """
    project: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_metrics: RequestMetrics = field(default_factory=RequestMetrics)
    duplicates: DuplicateAnalysisResult = field(default_factory=DuplicateAnalysisResult)
    similarity: SimilarityAnalysisResult = field(default_factory=SimilarityAnalysisResult)
    tokens: TokenStats = field(default_factory=TokenStats)
    latency: LatencyStats = field(default_factory=LatencyStats)
    efficiency: EfficiencyReport = field(default_factory=EfficiencyReport)
    optimization: OptimizationReport = field(default_factory=OptimizationReport)
    ecoscore: EcoScore = field(default_factory=EcoScore)
    energy_impact: Optional[EnergyEstimate] = None
    carbon_impact: Optional[CarbonEstimate] = None

    @property
    def recommendations(self) -> List[Any]:
        """Convenience property for list of recommendations."""
        return self.optimization.recommendations

    @property
    def savings(self) -> SavingsEstimate:
        """Convenience property for estimated savings."""
        return self.optimization.savings

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete report to JSON-friendly dictionary."""
        return {
            "project": self.project,
            "timestamp": self.timestamp,
            "request_metrics": self.request_metrics.to_dict(),
            "duplicates": self.duplicates.to_dict(),
            "similarity": self.similarity.to_dict(),
            "tokens": self.tokens.to_dict(),
            "latency": self.latency.to_dict(),
            "efficiency": self.efficiency.to_dict(),
            "optimization": self.optimization.to_dict(),
            "ecoscore": self.ecoscore.to_dict(),
            "energy_impact": self.energy_impact.to_dict() if self.energy_impact else None,
            "carbon_impact": self.carbon_impact.to_dict() if self.carbon_impact else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize report to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class WorkloadAnalyzer:
    """Orchestrates all EcoTrace analysis engines to generate a WorkloadReport."""

    def __init__(
        self,
        similarity_threshold: float = 0.60,
        similarity_analyzer: Optional[SimilarityAnalyzer] = None,
        optimizer: Optional[Optimizer] = None,
    ) -> None:


        self.duplicate_detector = DuplicateDetector()
        self.similarity_analyzer = (
            similarity_analyzer or EmbeddingSimilarityAnalyzer(threshold=similarity_threshold)
        )
        self.token_analyzer = TokenAnalyzer()
        self.latency_analyzer = LatencyAnalyzer()
        self.efficiency_analyzer = EfficiencyAnalyzer()
        self.optimizer = optimizer or Optimizer()
        self.ecoscore_calculator = EcoScoreCalculator()
        self.energy_estimator = EnergyEstimator()
        self.carbon_estimator = CarbonEstimator()

    def analyze_events(
        self,
        events: List[RequestEvent],
        project: Optional[str] = None,
        include_impact: bool = True,
    ) -> WorkloadReport:
        """Run full multi-phase analysis pipeline on a list of request events."""
        if not events:
            return WorkloadReport(project=project)

        # 1. Request metrics breakdown
        prov_cnt: Dict[str, int] = {}
        mod_cnt: Dict[str, int] = {}
        for e in events:
            if isinstance(e, RequestEvent):
                p = str(e.provider).lower()
                m = str(e.model).lower()
                prov_cnt[p] = prov_cnt.get(p, 0) + 1
                mod_cnt[m] = mod_cnt.get(m, 0) + 1

        req_metrics = RequestMetrics(
            total_requests=len(events),
            unique_providers=len(prov_cnt),
            unique_models=len(mod_cnt),
            provider_breakdown=prov_cnt,
            model_breakdown=mod_cnt,
        )

        # 2. Phase 1 — Duplicate Detection
        dup_res = self.duplicate_detector.analyze(events)

        # 3. Phase 2 & 3 — Semantic Similarity (excluding exact duplicates to prevent double counting)
        sim_res = self.similarity_analyzer.analyze_corpus(
            events, exclude_ids=dup_res.duplicate_event_ids
        )

        # 4. Phase 4 — Token Waste Analysis
        tok_res = self.token_analyzer.analyze(
            events, duplicate_result=dup_res, similarity_result=sim_res
        )

        # 5. Phase 5 — Latency Analysis
        lat_res = self.latency_analyzer.analyze(events)

        # 6. Phase 6 — Efficiency Report
        eff_res = self.efficiency_analyzer.analyze(
            events=events,
            duplicates=dup_res,
            similarity=sim_res,
            tokens=tok_res,
            latency=lat_res,
        )

        # 7. Phase 7, 8, 13 — Optimization & Savings & Simulation
        opt_res = self.optimizer.optimize(
            events=events,
            duplicates=dup_res,
            similarity=sim_res,
            tokens=tok_res,
            latency=lat_res,
        )

        # 8. Phase 11 — EcoScore
        ecoscore_res = self.ecoscore_calculator.calculate(
            events=events, efficiency_report=eff_res
        )

        # 9. Phase 12 — Optional Energy & Carbon Proxy Estimation
        energy_res: Optional[EnergyEstimate] = None
        carbon_res: Optional[CarbonEstimate] = None
        if include_impact:
            energy_res = self.energy_estimator.estimate(events)
            carbon_res = self.carbon_estimator.estimate(events)

        return WorkloadReport(
            project=project,
            request_metrics=req_metrics,
            duplicates=dup_res,
            similarity=sim_res,
            tokens=tok_res,
            latency=lat_res,
            efficiency=eff_res,
            optimization=opt_res,
            ecoscore=ecoscore_res,
            energy_impact=energy_res,
            carbon_impact=carbon_res,
        )
