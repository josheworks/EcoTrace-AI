"""Unit tests for semantic similarity analysis."""

import unittest
from ecotrace.analysis.similarity import (
    BasicSimilarityAnalyzer,
    EmbeddingSimilarityAnalyzer,
)
from ecotrace.storage.models import RequestEvent


class TestSimilarityAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = EmbeddingSimilarityAnalyzer(threshold=0.75)


    def test_identical_prompts(self):
        """Test similarity score for identical prompts."""
        e1 = RequestEvent(provider="openai", model="gpt-4o", prompt="Explain Python decorators")
        e2 = RequestEvent(provider="openai", model="gpt-4o", prompt="Explain Python decorators")
        res = self.analyzer.analyze(e2, [e1])
        self.assertTrue(res.is_similar)
        self.assertAlmostEqual(res.similarity_score, 1.0, places=2)

    def test_semantically_similar_prompts(self):
        """Test detection of semantically similar prompts with different phrasing."""
        e1 = RequestEvent(provider="openai", model="gpt-4o", prompt="Explain Python decorators in detail")
        e2 = RequestEvent(provider="openai", model="gpt-4o", prompt="Can you explain what Python decorators are")
        res = self.analyzer.analyze(e2, [e1])
        self.assertTrue(res.is_similar)
        self.assertGreaterEqual(res.similarity_score, 0.70)

    def test_clearly_different_prompts(self):
        """Test that distinct prompts do not trigger high similarity."""
        e1 = RequestEvent(provider="openai", model="gpt-4o", prompt="Explain Python decorators")
        e2 = RequestEvent(provider="openai", model="gpt-4o", prompt="What is quantum mechanics")
        res = self.analyzer.analyze(e2, [e1])
        self.assertFalse(res.is_similar)
        self.assertLess(res.similarity_score, 0.50)

    def test_threshold_behavior(self):
        """Test configurable similarity threshold."""
        strict_analyzer = EmbeddingSimilarityAnalyzer(threshold=0.99)
        lenient_analyzer = EmbeddingSimilarityAnalyzer(threshold=0.50)

        e1 = RequestEvent(provider="openai", model="gpt-4o", prompt="Explain machine learning basics")
        e2 = RequestEvent(provider="openai", model="gpt-4o", prompt="Give an overview of machine learning fundamentals")

        strict_res = strict_analyzer.analyze(e2, [e1])
        lenient_res = lenient_analyzer.analyze(e2, [e1])

        self.assertFalse(strict_res.is_similar)
        self.assertTrue(lenient_res.is_similar)

    def test_empty_corpus(self):
        """Test behavior when corpus is empty."""
        e1 = RequestEvent(provider="openai", model="gpt-4o", prompt="Test prompt")
        res = self.analyzer.analyze(e1, [])
        self.assertFalse(res.is_similar)
        self.assertEqual(res.similarity_score, 0.0)

    def test_message_list_prompts(self):
        """Test handling of chat completion message list prompts."""
        e1 = RequestEvent(
            provider="openai",
            model="gpt-4o",
            prompt=[{"role": "user", "content": "How to handle exceptions in Python?"}],
        )
        e2 = RequestEvent(
            provider="openai",
            model="gpt-4o",
            prompt=[{"role": "user", "content": "How to catch exceptions in Python?"}],
        )
        res = self.analyzer.analyze(e2, [e1])
        self.assertTrue(res.is_similar)

    def test_batch_corpus_analysis(self):
        """Test batch corpus similarity analysis."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="Explain decorators"),
            RequestEvent(provider="openai", model="gpt-4o", prompt="What is quantum mechanics"),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Explain decorators in detail"),
        ]
        res = self.analyzer.analyze_corpus(events)
        self.assertGreaterEqual(res.similar_pair_count, 1)


if __name__ == "__main__":
    unittest.main()
