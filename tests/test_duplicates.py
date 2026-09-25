"""Unit tests for duplicate request detection."""

import unittest
from ecotrace.analysis.duplicates import DuplicateDetector, DuplicateResult
from ecotrace.storage.models import RequestEvent


class TestDuplicateDetector(unittest.TestCase):
    def setUp(self):
        self.detector = DuplicateDetector()

    def test_no_duplicates(self):
        """Test dataset with zero duplicate requests."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="Prompt 1"),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Prompt 2"),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Prompt 3"),
        ]
        res = self.detector.analyze(events)
        self.assertEqual(res.total_events, 3)
        self.assertEqual(res.duplicate_count, 0)
        self.assertEqual(res.unique_count, 3)
        self.assertEqual(len(res.duplicate_groups), 0)

    def test_one_duplicate(self):
        """Test dataset with one duplicate request."""
        events = [
            RequestEvent(provider="openai", model="gpt-4o", prompt="Explain decorators", input_tokens=10, output_tokens=20, total_tokens=30),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Explain decorators", input_tokens=10, output_tokens=20, total_tokens=30),
        ]
        res = self.detector.analyze(events)
        self.assertEqual(res.total_events, 2)
        self.assertEqual(res.duplicate_count, 1)
        self.assertEqual(res.unique_count, 1)
        self.assertEqual(res.wasted_total_tokens, 30)
        self.assertEqual(len(res.duplicate_groups), 1)

    def test_multiple_duplicate_groups(self):
        """Test dataset with multiple distinct duplicate groups."""
        events = [
            # Group 1: 3 occurrences (2 duplicates)
            RequestEvent(provider="openai", model="gpt-4o", prompt="Group A", total_tokens=10),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Group A", total_tokens=10),
            RequestEvent(provider="openai", model="gpt-4o", prompt="Group A", total_tokens=10),
            # Group 2: 2 occurrences (1 duplicate)
            RequestEvent(provider="gemini", model="flash", prompt="Group B", total_tokens=20),
            RequestEvent(provider="gemini", model="flash", prompt="Group B", total_tokens=20),
            # Unique
            RequestEvent(provider="groq", model="llama", prompt="Unique C", total_tokens=5),
        ]
        res = self.detector.analyze(events)
        self.assertEqual(res.total_events, 6)
        self.assertEqual(res.duplicate_count, 3)  # 2 from Group A + 1 from Group B
        self.assertEqual(res.unique_count, 3)
        self.assertEqual(res.wasted_total_tokens, 40)  # 2*10 + 1*20
        self.assertEqual(len(res.duplicate_groups), 2)

    def test_empty_dataset(self):
        """Test empty event dataset."""
        res = self.detector.analyze([])
        self.assertEqual(res.total_events, 0)
        self.assertEqual(res.duplicate_count, 0)

    def test_missing_hash_handled_safely(self):
        """Test events without pre-computed request_hash."""
        e1 = RequestEvent(provider="openai", model="gpt-4o-mini", prompt="Test missing hash")
        e2 = RequestEvent(provider="openai", model="gpt-4o-mini", prompt="Test missing hash")
        e1.request_hash = None
        e2.request_hash = None

        res = self.detector.analyze([e1, e2])
        self.assertEqual(res.duplicate_count, 1)


if __name__ == "__main__":
    unittest.main()
