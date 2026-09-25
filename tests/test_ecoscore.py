"""Unit tests for EcoScore calculator."""

import unittest
from ecotrace.analysis.efficiency import EfficiencyReport
from ecotrace.impact.ecoscore import EcoScoreCalculator
from ecotrace.storage.models import RequestEvent


class TestEcoScoreCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = EcoScoreCalculator()

    def test_perfect_score_grade_A(self):
        """Test grade A score assignment."""
        events = [RequestEvent(provider="openai", model="gpt-4o", prompt="Unique P1")]
        eff = EfficiencyReport(efficiency_score=95.0)
        res = self.calculator.calculate(events, efficiency_report=eff)

        self.assertEqual(res.score, 95.0)
        self.assertEqual(res.grade, "A")

    def test_grade_assignments(self):
        """Test grade conversion logic."""
        self.assertEqual(self.calculator._score_to_grade(92.0), "A")
        self.assertEqual(self.calculator._score_to_grade(85.0), "B")
        self.assertEqual(self.calculator._score_to_grade(75.0), "C")
        self.assertEqual(self.calculator._score_to_grade(65.0), "D")
        self.assertEqual(self.calculator._score_to_grade(45.0), "F")


if __name__ == "__main__":
    unittest.main()
