"""Latency analysis module.

Computes latency statistics including mean, min, max, p50, p90, p95, and p99 percentiles
over tracked request events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ecotrace.storage.models import RequestEvent


@dataclass
class LatencyStats:
    """Aggregate latency statistics.

    Attributes:
        count: Number of requests analyzed.
        mean_latency_ms: Mean/average latency in milliseconds.
        avg_latency_ms: Alias for mean_latency_ms.
        min_latency_ms: Minimum latency in milliseconds.
        max_latency_ms: Maximum latency in milliseconds.
        p50_latency_ms: 50th percentile (median) latency.
        p90_latency_ms: 90th percentile latency.
        p95_latency_ms: 95th percentile latency.
        p99_latency_ms: 99th percentile latency.
        request_count: Alias for count.
    """
    count: int = 0
    mean_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p90_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    request_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "count": self.count,
            "mean_latency_ms": round(self.mean_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p90_latency_ms": round(self.p90_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
        }


class LatencyAnalyzer:
    """Analyzes latency characteristics across tracked events."""

    def analyze(self, events: List[RequestEvent]) -> LatencyStats:
        """Compute latency statistics over valid request latencies.

        Args:
            events: List of RequestEvent objects.

        Returns:
            LatencyStats object.
        """
        if not events:
            return LatencyStats()

        latencies = []
        for e in events:
            if not isinstance(e, RequestEvent):
                continue
            l = getattr(e, "latency_ms", 0.0)
            if l is not None and isinstance(l, (int, float)) and l >= 0:
                latencies.append(float(l))

        if not latencies:
            return LatencyStats(count=len(events), request_count=len(events))

        latencies.sort()
        n = len(latencies)
        mean_val = sum(latencies) / n

        p50 = self._percentile(latencies, 50)
        p90 = self._percentile(latencies, 90)
        p95 = self._percentile(latencies, 95)
        p99 = self._percentile(latencies, 99)

        return LatencyStats(
            count=n,
            mean_latency_ms=mean_val,
            avg_latency_ms=mean_val,
            min_latency_ms=latencies[0],
            max_latency_ms=latencies[-1],
            p50_latency_ms=p50,
            p90_latency_ms=p90,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            request_count=n,
        )

    @staticmethod
    def _percentile(sorted_values: List[float], pct: int) -> float:
        """Compute percentile using linear interpolation between closest ranks."""
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]

        k = (len(sorted_values) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(sorted_values):
            return sorted_values[f]
        d = k - f
        return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])
