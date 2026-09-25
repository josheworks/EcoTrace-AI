"""Unit tests for optimization strategies and optimizer engine."""

import unittest
from ecotrace.analysis.duplicates import DuplicateAnalysisResult
from ecotrace.analysis.latency import LatencyStats
from ecotrace.analysis.similarity import SimilarityAnalysisResult, SimilarityPair
from ecotrace.optimization.optimizer import Optimizer
from ecotrace.optimization.strategies import (
    ContextReductionStrategy,
    ExactCachingStrategy,
    HighLatencyStrategy,
    ModelRightSizingStrategy,
    SemanticCachingStrategy,
)
from ecotrace.storage.models import RequestEvent


class TestOptimizationStrategies(unittest.TestCase):
    def setUp(self):
        self.optimizer = Optimizer()

    def test_caching_strategy_trigger(self):
        """Test exact caching strategy triggers on duplicates."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="Repeat", total_tokens=100),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Repeat", total_tokens=100),
        ]
        dup_res = DuplicateAnalysisResult(duplicate_count=1, wasted_total_tokens=100)
        res = ExactCachingStrategy().evaluate(events, duplicates=dup_res)
        self.assertTrue(res.applicable)
        self.assertEqual(res.estimated_savings["requests_avoided"], 1)

    def test_semantic_caching_strategy(self):
        """Test semantic caching strategy triggers on similar prompts."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="Prompt A"),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Prompt B"),
        ]
        sim_res = SimilarityAnalysisResult(
            similar_pair_count=1,
            potential_redundant_tokens=150,
        )
        res = SemanticCachingStrategy().evaluate(events, similarity=sim_res)
        self.assertTrue(res.applicable)
        self.assertEqual(res.estimated_savings["potential_tokens_avoided"], 150)

    def test_context_reduction_strategy(self):
        """Test context reduction strategy triggers on large prompts."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="Large prompt", input_tokens=2500),
        ]
        res = ContextReductionStrategy(high_token_threshold=1500).evaluate(events)
        self.assertTrue(res.applicable)
        self.assertGreater(res.estimated_savings["potential_tokens_avoided"], 0)

    def test_high_latency_strategy(self):
        """Test high latency strategy triggers on p95 latency spike."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="P1", latency_ms=3500.0),
        ]
        lat_res = LatencyStats(p95_latency_ms=3500.0)
        res = HighLatencyStrategy(latency_threshold_ms=2000.0).evaluate(events, latency=lat_res)
        self.assertTrue(res.applicable)

    def test_optimizer_full_report(self):
        """Test full optimizer report generation."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="Repeat", total_tokens=100),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Repeat", total_tokens=100),
        ]
        report = self.optimizer.optimize(events)
        self.assertGreaterEqual(len(report.recommendations), 1)
        self.assertEqual(report.savings.requests_avoided, 1)


if __name__ == "__main__":
    unittest.main()
