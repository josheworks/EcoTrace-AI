"""Latency analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ecotrace.storage.models import RequestEvent


@dataclass
class LatencyStats:
    """Aggregate latency statistics.

    Attributes:
        avg_latency_ms: Average latency in milliseconds.
        max_latency_ms: Maximum latency in milliseconds.
        min_latency_ms: Minimum latency in milliseconds.
        p50_latency_ms: Median latency (50th percentile).
        p95_latency_ms: 95th percentile latency.
        p99_latency_ms: 99th percentile latency.
        request_count: Number of requests analyzed.
    """
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    request_count: int = 0


class LatencyAnalyzer:
    """Analyzes latency across tracked events."""

    def analyze(self, events: List[RequestEvent]) -> LatencyStats:
        """Compute latency statistics.

        Args:
            events: List of RequestEvent objects.

        Returns:
            LatencyStats with computed aggregates.
        """
        if not events:
            return LatencyStats()

        latencies = sorted(e.latency_ms for e in events)
        n = len(latencies)

        return LatencyStats(
            avg_latency_ms=sum(latencies) / n,
            max_latency_ms=latencies[-1],
            min_latency_ms=latencies[0],
            p50_latency_ms=self._percentile(latencies, 50),
            p95_latency_ms=self._percentile(latencies, 95),
            p99_latency_ms=self._percentile(latencies, 99),
            request_count=n,
        )

    @staticmethod
    def _percentile(sorted_values: List[float], pct: int) -> float:
        """Compute a percentile from a sorted list."""
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * (pct / 100)
        f = int(k)
        c = f + 1
        if c >= len(sorted_values):
            return sorted_values[f]
        d = k - f
        return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])
