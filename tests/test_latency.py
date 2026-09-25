"""Unit tests for latency analysis and percentiles."""

import unittest
from ecotrace.analysis.latency import LatencyAnalyzer
from ecotrace.storage.models import RequestEvent


class TestLatencyAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = LatencyAnalyzer()

    def test_latency_percentiles(self):
        """Test p50, p90, p95, p99 percentiles calculation."""
        # 10 events with latencies 100, 200, 300, ... 1000 ms
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt=f"P{i}", latency_ms=i * 100.0)
            for i in range(1, 11)
        ]
        stats = self.analyzer.analyze(events)

        self.assertEqual(stats.count, 10)
        self.assertEqual(stats.min_latency_ms, 100.0)
        self.assertEqual(stats.max_latency_ms, 1000.0)
        self.assertEqual(stats.mean_latency_ms, 550.0)
        self.assertAlmostEqual(stats.p50_latency_ms, 550.0, places=1)
        self.assertGreaterEqual(stats.p95_latency_ms, 900.0)
        self.assertGreaterEqual(stats.p99_latency_ms, 950.0)

    def test_single_event(self):
        """Test latency analysis for a single event."""
        events = [RequestEvent(provider="openai", model="gpt-4o", prompt="P1", latency_ms=250.0)]
        stats = self.analyzer.analyze(events)
        self.assertEqual(stats.count, 1)
        self.assertEqual(stats.p50_latency_ms, 250.0)
        self.assertEqual(stats.p95_latency_ms, 250.0)

    def test_empty_and_zero_latency(self):
        """Test latency analysis with empty list or zero latencies."""
        stats_empty = self.analyzer.analyze([])
        self.assertEqual(stats_empty.count, 0)

        events_zero = [RequestEvent(provider="openai", model="gpt-4o", prompt="P1", latency_ms=0.0)]
        stats_zero = self.analyzer.analyze(events_zero)
        self.assertEqual(stats_zero.count, 1)
        self.assertEqual(stats_zero.p50_latency_ms, 0.0)


if __name__ == "__main__":
    unittest.main()
