"""Tests for tracking layer components."""

import unittest
from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.storage.memory import MemoryStorage
from ecotrace.tracking.session import Session
from ecotrace.tracking.tracker import Tracker


class TestTracking(unittest.TestCase):
    def test_tracker_event_creation(self):
        """Test Tracker creates and stores RequestEvent objects."""
        storage = MemoryStorage()
        session = Session(project="test-project")
        tracker = Tracker(storage=storage, session=session)

        req = RequestCapture(prompt="Test prompt", provider="openai", model="gpt-4o-mini")
        resp = ResponseCapture(response="Test response", input_tokens=5, output_tokens=10)

        result = tracker.track(request=req, response=resp, latency_ms=50.0)

        self.assertEqual(result.event.provider, "openai")
        self.assertEqual(result.event.model, "gpt-4o-mini")
        self.assertEqual(result.event.prompt, "Test prompt")
        self.assertEqual(result.event.response, "Test response")
        self.assertEqual(result.event.input_tokens, 5)
        self.assertEqual(result.event.output_tokens, 10)
        self.assertEqual(result.event.total_tokens, 15)
        self.assertEqual(result.event.latency_ms, 50.0)
        self.assertEqual(result.event.session_id, session.session_id)
        self.assertIsNotNone(result.event.request_hash)

        # Check session counter
        self.assertEqual(session.event_count, 1)
        self.assertEqual(tracker.count(), 1)

    def test_tracker_event_lifecycle_hooks(self):
        """Test Tracker event emitter callbacks."""
        storage = MemoryStorage()
        tracker = Tracker(storage=storage)

        events_emitted = []

        def on_before_track(name, data):
            events_emitted.append(("before", name, data))

        def on_after_track(name, data):
            events_emitted.append(("after", name, data))

        tracker.events.on("before_track", on_before_track)
        tracker.events.on("after_track", on_after_track)

        req = RequestCapture(prompt="Hello", provider="generic", model="custom")
        tracker.track(request=req)

        self.assertEqual(len(events_emitted), 2)
        self.assertEqual(events_emitted[0][0], "before")
        self.assertEqual(events_emitted[1][0], "after")


if __name__ == "__main__":
    unittest.main()

