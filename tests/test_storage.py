"""Tests for storage backends (MemoryStorage and SQLiteStorage)."""

import os
import tempfile
import unittest
from ecotrace.storage.memory import MemoryStorage
from ecotrace.storage.models import RequestEvent
from ecotrace.storage.sqlite import SQLiteStorage


class TestStorage(unittest.TestCase):
    def test_memory_storage_crud(self):
        """Test MemoryStorage save, get, query, count, and clear operations."""
        storage = MemoryStorage()

        event1 = RequestEvent(
            provider="openai",
            model="gpt-4o-mini",
            prompt="Prompt 1",
            response="Response 1",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            session_id="sess-1",
        )
        event2 = RequestEvent(
            provider="gemini",
            model="gemini-1.5-flash",
            prompt="Prompt 2",
            response="Response 2",
            input_tokens=15,
            output_tokens=25,
            total_tokens=40,
            session_id="sess-1",
        )

        storage.save_event(event1)
        storage.save_event(event2)

        # get_event
        retrieved = storage.get_event(event1.request_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.request_id, event1.request_id)
        self.assertEqual(retrieved.prompt, "Prompt 1")

        # count_events
        self.assertEqual(storage.count_events(), 2)
        self.assertEqual(storage.count_events(session_id="sess-1"), 2)
        self.assertEqual(storage.count_events(provider="openai"), 1)

        # get_events
        events = storage.get_events(provider="openai")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].provider, "openai")

        # clear
        storage.clear()
        self.assertEqual(storage.count_events(), 0)

    def test_sqlite_storage_crud(self):
        """Test SQLiteStorage save, get, query, count, and clear operations."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            storage = SQLiteStorage(db_path=db_path)

            event1 = RequestEvent(
                provider="openai",
                model="gpt-4o-mini",
                prompt="Prompt 1",
                response="Response 1",
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                session_id="sess-1",
                metadata={"environment": "test"},
            )
            event2 = RequestEvent(
                provider="groq",
                model="llama-3.1-70b",
                prompt=[{"role": "user", "content": "Prompt 2"}],
                response="Response 2",
                input_tokens=15,
                output_tokens=25,
                total_tokens=40,
                session_id="sess-2",
            )

            storage.save_event(event1)
            storage.save_event(event2)

            # get_event
            retrieved1 = storage.get_event(event1.request_id)
            self.assertIsNotNone(retrieved1)
            self.assertEqual(retrieved1.request_id, event1.request_id)
            self.assertEqual(retrieved1.prompt, "Prompt 1")
            self.assertEqual(retrieved1.metadata, {"environment": "test"})

            retrieved2 = storage.get_event(event2.request_id)
            self.assertIsNotNone(retrieved2)
            self.assertIsInstance(retrieved2.prompt, list)

            # count_events
            self.assertEqual(storage.count_events(), 2)
            self.assertEqual(storage.count_events(session_id="sess-1"), 1)
            self.assertEqual(storage.count_events(provider="groq"), 1)

            # get_events
            events = storage.get_events(provider="openai")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].model, "gpt-4o-mini")

            # clear
            storage.clear()
            self.assertEqual(storage.count_events(), 0)
            storage.close()

        finally:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()

