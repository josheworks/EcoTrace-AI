import unittest

from ecotrace.analysis.report import WorkloadAnalyzer
from ecotrace.analysis.tokens import TokenAnalyzer
from ecotrace.impact.cost import CostCalculator
from ecotrace.optimization.optimizer import Optimizer
from ecotrace.storage.models import RequestEvent


class TestCoreAnalysisContracts(unittest.TestCase):
    def test_exact_duplicate_tokens_are_not_double_counted(self):
        events = [
            RequestEvent(
                provider="openai",
                model="gpt-4o-mini",
                prompt="Explain Python decorators",
                input_tokens=120,
                output_tokens=80,
                total_tokens=200,
            ),
            RequestEvent(
                provider="openai",
                model="gpt-4o-mini",
                prompt="Explain Python decorators",
                input_tokens=120,
                output_tokens=80,
                total_tokens=200,
            ),
            RequestEvent(
                provider="openai",
                model="gpt-4o-mini",
                prompt="Can you explain decorators in Python?",
                input_tokens=130,
                output_tokens=90,
                total_tokens=220,
            ),
        ]

        dup = WorkloadAnalyzer().duplicate_detector.analyze(events)
        sim = WorkloadAnalyzer().similarity_analyzer.analyze_corpus(events, exclude_ids=dup.duplicate_event_ids)
        token_stats = TokenAnalyzer().analyze(events, duplicate_result=dup, similarity_result=sim)

        self.assertEqual(token_stats.duplicate_tokens, 200)
        self.assertEqual(token_stats.potential_semantic_redundant_tokens, 220)
        self.assertEqual(token_stats.total_potential_waste, 420)

    def test_unknown_model_pricing_returns_none(self):
        calc = CostCalculator(pricing={})
        events = [
            RequestEvent(provider="openai", model="mystery-model", prompt="hello", input_tokens=1000, output_tokens=500, total_tokens=1500)
        ]
        estimate = calc.estimate(events)
        self.assertIsNone(estimate.total_cost_usd)

    def test_optimizer_distinguishes_confirmed_and_potential_savings(self):
        events = [
            RequestEvent(provider="openai", model="gpt-4o-mini", prompt="Explain Python decorators", input_tokens=100, output_tokens=50, total_tokens=150),
            RequestEvent(provider="openai", model="gpt-4o-mini", prompt="Explain Python decorators", input_tokens=100, output_tokens=50, total_tokens=150),
            RequestEvent(provider="openai", model="gpt-4o-mini", prompt="Can you explain decorators in Python?", input_tokens=110, output_tokens=60, total_tokens=170),
        ]

        report = Optimizer().optimize(events)
        self.assertEqual(report.savings.exact_requests_avoided, 1)
        self.assertEqual(report.savings.semantic_requests_avoidable, 1)
        self.assertGreaterEqual(report.simulation.original_requests, 3)
        self.assertGreaterEqual(report.simulation.requests_avoided, 1)
        self.assertIn("assumptions", report.simulation.details)


if __name__ == "__main__":
    unittest.main()
