"""Unit tests for token waste analysis."""

import unittest
from ecotrace.analysis.duplicates import DuplicateAnalysisResult
from ecotrace.analysis.similarity import SimilarityAnalysisResult
from ecotrace.analysis.tokens import TokenAnalyzer
from ecotrace.storage.models import RequestEvent


class TestTokenAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = TokenAnalyzer()

    def test_normal_token_usage(self):
        """Test calculation of normal token statistics."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="P1", input_tokens=100, output_tokens=50, total_tokens=150),
            RequestEvent(provider="openai", model="gpt-4o", prompt="P2", input_tokens=200, output_tokens=100, total_tokens=300),
        ]
        stats = self.analyzer.analyze(events)
        self.assertEqual(stats.total_input_tokens, 300)
        self.assertEqual(stats.total_output_tokens, 150)
        self.assertEqual(stats.total_tokens, 450)
        self.assertEqual(stats.avg_total_tokens, 225.0)

    def test_token_waste_integration(self):
        """Test token waste breakdown with duplicate and similarity results."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="P1", input_tokens=100, output_tokens=50, total_tokens=150),
            RequestEvent(provider="openai", model="gpt-4o", prompt="P1", input_tokens=100, output_tokens=50, total_tokens=150),
        ]
        dup_res = DuplicateAnalysisResult(
            wasted_input_tokens=100,
            wasted_output_tokens=50,
            wasted_total_tokens=150,
        )
        sim_res = SimilarityAnalysisResult(
            potential_redundant_tokens=50,
        )

        stats = self.analyzer.analyze(events, duplicate_result=dup_res, similarity_result=sim_res)
        self.assertEqual(stats.duplicate_tokens, 150)
        self.assertEqual(stats.potential_semantic_redundant_tokens, 50)
        self.assertEqual(stats.total_wasted_tokens, 200)

    def test_no_events(self):
        """Test behavior when events list is empty."""
        stats = self.analyzer.analyze([])
        self.assertEqual(stats.total_tokens, 0)
        self.assertEqual(stats.request_count, 0)


if __name__ == "__main__":
    unittest.main()
