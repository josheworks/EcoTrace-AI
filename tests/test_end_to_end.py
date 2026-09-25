"""End-to-end integration tests for the full EcoTrace AI pipeline."""

import unittest
from ecotrace.client import EcoTrace
from ecotrace.analysis.report import WorkloadReport


class TestEndToEndPipeline(unittest.TestCase):
    def test_full_pipeline_analysis(self):
        """Test complete pipeline from tracking events to generating unified WorkloadReport."""
        eco = EcoTrace(project="e2e-test")

        # 1. Track realistic mix of requests (duplicates, similar requests, high context)
        mock_resp = {
            "choices": [{"message": {"content": "Response content"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        }

        # Duplicate pair 1
        eco.track(
            provider="openai",
            model="gpt-4o",
            prompt="Explain Python decorators",
            response=mock_resp,
            latency_ms=250.0,
        )
        eco.track(
            provider="openai",
            model="gpt-4o",
            prompt="Explain Python decorators",
            response=mock_resp,
            latency_ms=210.0,
        )

        # Semantically similar prompt
        eco.track(
            provider="openai",
            model="gpt-4o",
            prompt="Can you explain what Python decorators are",
            response=mock_resp,
            latency_ms=300.0,
        )

        # High-context query
        eco.track(
            provider="gemini",
            model="gemini-1.5-pro",
            prompt="Summarize this massive document: " + ("lorem ipsum " * 300),
            response=mock_resp,
            latency_ms=1200.0,
        )


        # 2. Run analysis
        report = eco.analyze()

        # 3. Assert report structure & metrics
        self.assertIsInstance(report, WorkloadReport)
        self.assertEqual(report.request_metrics.total_requests, 4)
        self.assertEqual(report.duplicates.duplicate_count, 1)
        self.assertGreaterEqual(report.similarity.similar_pair_count, 1)
        self.assertGreater(report.tokens.total_tokens, 0)
        self.assertGreater(report.latency.count, 0)

        # Efficiency & EcoScore
        self.assertGreater(report.efficiency.efficiency_score, 0.0)
        self.assertIn(report.ecoscore.grade, ["A", "B", "C", "D", "F"])

        # Recommendations & Savings
        self.assertGreaterEqual(len(report.recommendations), 1)
        self.assertEqual(report.savings.requests_avoided, 1)

        # Test dictionary and JSON serialization
        d = report.to_dict()
        self.assertEqual(d["request_metrics"]["total_requests"], 4)
        j = report.to_json()
        self.assertIn("efficiency", j)
        self.assertIn("ecoscore", j)


if __name__ == "__main__":
    unittest.main()
