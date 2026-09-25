"""Workload efficiency analysis module.

Produces a transparent, multi-signal efficiency report that evaluates AI workload efficiency
on a scale from 0 to 100 based on request redundancy, token waste, and latency.

FORMULA & METRIC WEIGHTS:
-------------------------
1. Request Efficiency (Weight: 40%)
   - Formula: max(0, 100.0 * (1.0 - (duplicate_count / total_requests)))

2. Token Efficiency (Weight: 40%)
   - Formula: max(0, 100.0 * (1.0 - (total_wasted_tokens / total_tokens)))

3. Latency Efficiency (Weight: 20%)
   - Formula: 100.0 if p95_latency <= 1000ms, scaling down to 0 at 5000ms+.

4. Redundancy Penalty
   - Subtracted penalty based on ratio of semantically similar requests: min(20, (similar_count / total_requests) * 20)

Overall Efficiency Score:
   Score = max(0.0, min(100.0, (0.40 * RequestEff) + (0.40 * TokenEff) + (0.20 * LatencyEff) - RedundancyPenalty))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ecotrace.analysis.duplicates import DuplicateAnalysisResult
from ecotrace.analysis.latency import LatencyStats
from ecotrace.analysis.similarity import SimilarityAnalysisResult
from ecotrace.analysis.tokens import TokenStats
from ecotrace.storage.models import RequestEvent


@dataclass
class EfficiencyReport:
    """Multi-signal workload efficiency report.

    Attributes:
        total_requests: Total number of requests analyzed.
        duplicate_count: Number of exact duplicate requests.
        similar_count: Number of semantically similar requests.
        estimated_wasted_tokens: Tokens lost to duplicates and redundancies.
        efficiency_score: Overall efficiency score (0.0 to 100.0).
        score: Alias for efficiency_score.
        request_efficiency: Sub-score for request uniqueness (0-100).
        token_efficiency: Sub-score for non-wasteful token usage (0-100).
        latency_efficiency: Sub-score for response latency (0-100).
        redundancy_penalty: Penalty points deducted for semantic redundancy.
        components: Dictionary of raw sub-score components.
        recommendations: High-level recommendations based on sub-scores.
        details: Additional context metrics.
    """
    total_requests: int = 0
    duplicate_count: int = 0
    similar_count: int = 0
    estimated_wasted_tokens: int = 0
    efficiency_score: float = 100.0
    score: float = 100.0
    request_efficiency: float = 100.0
    token_efficiency: float = 100.0
    latency_efficiency: float = 100.0
    redundancy_penalty: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to a dictionary."""
        return {
            "total_requests": self.total_requests,
            "duplicate_count": self.duplicate_count,
            "similar_count": self.similar_count,
            "estimated_wasted_tokens": self.estimated_wasted_tokens,
            "efficiency_score": round(self.efficiency_score, 1),
            "score": round(self.score, 1),
            "request_efficiency": round(self.request_efficiency, 1),
            "token_efficiency": round(self.token_efficiency, 1),
            "latency_efficiency": round(self.latency_efficiency, 1),
            "redundancy_penalty": round(self.redundancy_penalty, 1),
            "components": {k: round(v, 1) for k, v in self.components.items()},
            "recommendations": list(self.recommendations),
            "details": self.details,
        }


class EfficiencyAnalyzer:
    """Analyzes overall AI workload efficiency across multiple signals."""

    def analyze(
        self,
        events: List[RequestEvent],
        duplicates: Optional[DuplicateAnalysisResult] = None,
        similarity: Optional[SimilarityAnalysisResult] = None,
        tokens: Optional[TokenStats] = None,
        latency: Optional[LatencyStats] = None,
    ) -> EfficiencyReport:
        """Produce a transparent multi-signal efficiency report.

        Args:
            events: Raw list of RequestEvent objects.
            duplicates: Result from DuplicateDetector.
            similarity: Result from SimilarityAnalyzer.
            tokens: Result from TokenAnalyzer.
            latency: Result from LatencyAnalyzer.

        Returns:
            An EfficiencyReport instance.
        """
        if not events:
            return EfficiencyReport(
                components={
                    "request_efficiency": 100.0,
                    "token_efficiency": 100.0,
                    "latency_efficiency": 100.0,
                    "redundancy_penalty": 0.0,
                }
            )

        n = len(events)
        dup_cnt = duplicates.duplicate_count if duplicates else 0
        sim_cnt = similarity.similar_pair_count if similarity else 0
        wasted_tok = (tokens.total_wasted_tokens if tokens else 0) or (
            duplicates.wasted_total_tokens if duplicates else 0
        )
        total_tok = tokens.total_tokens if tokens else sum(e.total_tokens for e in events)

        # 1. Request Efficiency (40%)
        req_eff = max(0.0, 100.0 * (1.0 - (dup_cnt / n))) if n > 0 else 100.0

        # 2. Token Efficiency (40%)
        if total_tok > 0:
            tok_eff = max(0.0, 100.0 * (1.0 - (wasted_tok / total_tok)))
        else:
            tok_eff = 100.0

        # 3. Latency Efficiency (20%)
        p95 = latency.p95_latency_ms if latency else 0.0
        if p95 <= 1000.0:
            lat_eff = 100.0
        elif p95 >= 5000.0:
            lat_eff = 20.0
        else:
            lat_eff = 100.0 - (80.0 * ((p95 - 1000.0) / 4000.0))

        # 4. Redundancy Penalty (Deduction up to 20 pts)
        sim_ratio = (sim_cnt / n) if n > 0 else 0.0
        red_penalty = min(20.0, sim_ratio * 20.0)

        # Overall composite score
        raw_score = (0.40 * req_eff) + (0.40 * tok_eff) + (0.20 * lat_eff) - red_penalty
        final_score = max(0.0, min(100.0, raw_score))

        # Build human-readable recommendations
        recs: List[str] = []
        if dup_cnt > 0:
            recs.append(f"Cache response for {dup_cnt} exact duplicate request(s).")
        if sim_cnt > 0:
            recs.append(f"Standardize prompts for {sim_cnt} semantically similar request(s).")
        if tok_eff < 80.0:
            recs.append(f"Trim context history to recover estimated ~{wasted_tok} wasted tokens.")
        if lat_eff < 70.0:
            recs.append("Consider model right-sizing or streaming to reduce p95 response latency.")

        components = {
            "request_efficiency": req_eff,
            "token_efficiency": tok_eff,
            "latency_efficiency": lat_eff,
            "redundancy_penalty": red_penalty,
        }

        return EfficiencyReport(
            total_requests=n,
            duplicate_count=dup_cnt,
            similar_count=sim_cnt,
            estimated_wasted_tokens=wasted_tok,
            efficiency_score=final_score,
            score=final_score,
            request_efficiency=req_eff,
            token_efficiency=tok_eff,
            latency_efficiency=lat_eff,
            redundancy_penalty=red_penalty,
            components=components,
            recommendations=recs,
            details={
                "total_tokens": total_tok,
                "p95_latency_ms": p95,
            },
        )
