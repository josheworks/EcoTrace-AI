"""EcoTrace analysis modules."""

from ecotrace.analysis.duplicates import DuplicateAnalysisResult, DuplicateDetector, DuplicateGroup
from ecotrace.analysis.efficiency import EfficiencyAnalyzer, EfficiencyReport
from ecotrace.analysis.latency import LatencyAnalyzer, LatencyStats
from ecotrace.analysis.report import WorkloadAnalyzer, WorkloadReport
from ecotrace.analysis.similarity import (
    BasicSimilarityAnalyzer,
    EmbeddingSimilarityAnalyzer,
    SimilarityAnalysisResult,
    SimilarityAnalyzer,
    SimilarityPair,
)
from ecotrace.analysis.tokens import TokenAnalyzer, TokenStats

__all__ = [
    "DuplicateDetector",
    "DuplicateAnalysisResult",
    "DuplicateGroup",
    "SimilarityAnalyzer",
    "EmbeddingSimilarityAnalyzer",
    "BasicSimilarityAnalyzer",
    "SimilarityAnalysisResult",
    "SimilarityPair",
    "TokenAnalyzer",
    "TokenStats",
    "LatencyAnalyzer",
    "LatencyStats",
    "EfficiencyAnalyzer",
    "EfficiencyReport",
    "WorkloadAnalyzer",
    "WorkloadReport",
]
