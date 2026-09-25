"""Unit tests for workload efficiency analysis."""

import unittest
from ecotrace.analysis.duplicates import DuplicateAnalysisResult
from ecotrace.analysis.efficiency import EfficiencyAnalyzer
from ecotrace.analysis.latency import LatencyStats
from ecotrace.analysis.tokens import TokenStats
from ecotrace.storage.models import RequestEvent


class TestEfficiencyAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = EfficiencyAnalyzer()

    def test_100_percent_unique_workload(self):
        """Test efficiency score for a perfectly unique, fast workload."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="P1", total_tokens=100, latency_ms=100.0),
            RequestEvent(provider="openai", model="gpt-4o", prompt="P2", total_tokens=100, latency_ms=100.0),
        ]
        dup_res = DuplicateAnalysisResult(duplicate_count=0)
        tok_res = TokenStats(total_tokens=200, total_wasted_tokens=0)
        lat_res = LatencyStats(p95_latency_ms=100.0)

        rep = self.analyzer.analyze(events, duplicates=dup_res, tokens=tok_res, latency=lat_res)
        self.assertEqual(rep.efficiency_score, 100.0)
        self.assertEqual(rep.request_efficiency, 100.0)

    def test_duplicate_heavy_workload(self):
        """Test efficiency score drop for a duplicate-heavy workload."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="P1", total_tokens=100),
            RequestEvent(provider="openai", model="gpt-4o", prompt="P1", total_tokens=100),
        ]
        dup_res = DuplicateAnalysisResult(total_events=2, duplicate_count=1, wasted_total_tokens=100)
        tok_res = TokenStats(total_tokens=200, total_wasted_tokens=100)

        rep = self.analyzer.analyze(events, duplicates=dup_res, tokens=tok_res)
        self.assertLess(rep.efficiency_score, 80.0)
        self.assertEqual(rep.duplicate_count, 1)


if __name__ == "__main__":
    unittest.main()
