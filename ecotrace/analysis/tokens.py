"""Token usage analysis module.

Analyzes token consumption and quantifies exact duplicate token waste
and potential semantic redundancy token waste.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ecotrace.analysis.duplicates import DuplicateAnalysisResult
from ecotrace.analysis.similarity import SimilarityAnalysisResult
from ecotrace.storage.models import RequestEvent


@dataclass
class TokenStats:
    """Aggregate token usage statistics and waste metrics.

    Exact duplicate waste is confirmed redundant work.
    Semantic redundancy is a potential signal and is kept separate.
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    avg_total_tokens: float = 0.0
    max_input_tokens: int = 0
    max_output_tokens: int = 0
    duplicate_input_tokens: int = 0
    duplicate_output_tokens: int = 0
    duplicate_tokens: int = 0
    potential_semantic_redundant_tokens: int = 0
    total_wasted_tokens: int = 0
    request_count: int = 0

    @property
    def exact_duplicate_tokens(self) -> int:
        """Confirmed waste attributable to exact duplicate requests."""
        return self.duplicate_tokens

    @property
    def total_potential_waste(self) -> int:
        """Total combined potential waste from exact duplicates and semantic redundancy."""
        return self.total_wasted_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "avg_input_tokens": round(self.avg_input_tokens, 2),
            "avg_output_tokens": round(self.avg_output_tokens, 2),
            "avg_total_tokens": round(self.avg_total_tokens, 2),
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "duplicate_input_tokens": self.duplicate_input_tokens,
            "duplicate_output_tokens": self.duplicate_output_tokens,
            "duplicate_tokens": self.duplicate_tokens,
            "exact_duplicate_tokens": self.exact_duplicate_tokens,
            "potential_semantic_redundant_tokens": self.potential_semantic_redundant_tokens,
            "total_potential_waste": self.total_potential_waste,
            "total_wasted_tokens": self.total_wasted_tokens,
            "request_count": self.request_count,
        }


class TokenAnalyzer:
    """Analyzes token usage across tracked events."""

    def analyze(
        self,
        events: List[RequestEvent],
        duplicate_result: Optional[DuplicateAnalysisResult] = None,
        similarity_result: Optional[SimilarityAnalysisResult] = None,
    ) -> TokenStats:
        """Compute aggregate token statistics and waste breakdown.

        Args:
            events: List of RequestEvent objects.
            duplicate_result: Optional result from DuplicateDetector.
            similarity_result: Optional result from SimilarityAnalyzer.

        Returns:
            TokenStats object.
        """
        if not events:
            return TokenStats()

        total_in = sum(getattr(e, "input_tokens", 0) for e in events)
        total_out = sum(getattr(e, "output_tokens", 0) for e in events)
        total = sum(getattr(e, "total_tokens", 0) for e in events)
        n = len(events)

        dup_in = duplicate_result.wasted_input_tokens if duplicate_result else 0
        dup_out = duplicate_result.wasted_output_tokens if duplicate_result else 0
        dup_tot = duplicate_result.wasted_total_tokens if duplicate_result else 0

        potential_sem = similarity_result.potential_redundant_tokens if similarity_result else 0
        total_wasted = dup_tot + potential_sem

        max_in = max((getattr(e, "input_tokens", 0) for e in events), default=0)
        max_out = max((getattr(e, "output_tokens", 0) for e in events), default=0)

        return TokenStats(
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_tokens=total,
            avg_input_tokens=total_in / n if n > 0 else 0.0,
            avg_output_tokens=total_out / n if n > 0 else 0.0,
            avg_total_tokens=total / n if n > 0 else 0.0,
            max_input_tokens=max_in,
            max_output_tokens=max_out,
            duplicate_input_tokens=dup_in,
            duplicate_output_tokens=dup_out,
            duplicate_tokens=dup_tot,
            potential_semantic_redundant_tokens=potential_sem,
            total_wasted_tokens=total_wasted,
            request_count=n,
        )
