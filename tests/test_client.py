"""Tests for EcoTrace client public API."""

import unittest
from ecotrace.client import EcoTrace
from ecotrace.config import EcoTraceConfig
from ecotrace.storage.memory import MemoryStorage
from ecotrace.storage.models import RequestEvent, TrackingResult


class TestClient(unittest.TestCase):
    def test_client_init_defaults(self):
        """Test initializing EcoTrace client with default options."""
        eco = EcoTrace()
        self.assertTrue(eco.config.enabled)
        self.assertEqual(eco.config.storage, "memory")
        self.assertIsInstance(eco.storage, MemoryStorage)

    def test_client_init_with_config(self):
        """Test initializing EcoTrace client with custom config."""
        config = EcoTraceConfig(project="my-project", enabled=False)
        eco = EcoTrace(config=config)
        self.assertEqual(eco.config.project, "my-project")
        self.assertFalse(eco.config.enabled)

    def test_basic_tracking(self):
        """Test tracking a simple request."""
        eco = EcoTrace()
        result = eco.track(
            provider="openai",
            model="gpt-4o-mini",
            prompt="Explain quantum computing",
            response="Quantum computing uses qubits...",
            latency_ms=120.5,
        )

        self.assertIsInstance(result, TrackingResult)
        self.assertIsInstance(result.event, RequestEvent)
        self.assertEqual(result.event.provider, "openai")
        self.assertEqual(result.event.model, "gpt-4o-mini")
        self.assertEqual(result.event.response, "Quantum computing uses qubits...")
        self.assertEqual(result.event.latency_ms, 120.5)

    def test_disabled_tracking(self):
        """Test tracking when client is disabled."""
        eco = EcoTrace(enabled=False)
        result = eco.track(
            provider="openai",
            model="gpt-4o-mini",
            prompt="Test prompt",
        )

        self.assertEqual(result.event.provider, "openai")
        self.assertEqual(len(eco.get_events()), 0)

    def test_get_events_and_clear(self):
        """Test retrieving and clearing stored events."""
        eco = EcoTrace()
        eco.track(provider="openai", model="gpt-4o-mini", prompt="Prompt 1")
        eco.track(provider="gemini", model="gemini-1.5-flash", prompt="Prompt 2")

        events = eco.get_events()
        self.assertEqual(len(events), 2)

        openai_events = eco.get_events(provider="openai")
        self.assertEqual(len(openai_events), 1)
        self.assertEqual(openai_events[0].provider, "openai")

        eco.clear()
        self.assertEqual(len(eco.get_events()), 0)

    def test_package_imports(self):
        """Test root package imports."""
        import ecotrace

        self.assertTrue(hasattr(ecotrace, "EcoTrace"))
        self.assertTrue(hasattr(ecotrace, "RequestEvent"))
        self.assertTrue(hasattr(ecotrace, "track"))


if __name__ == "__main__":
    unittest.main()

