"""Tests for EcoTrace dashboard API endpoints and None cost compatibility."""

import unittest
from fastapi.testclient import TestClient

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.dashboard.app import create_app
from ecotrace.dashboard.seed import seed_database
from ecotrace.storage.memory import MemoryStorage
from ecotrace.tracking.tracker import Tracker


class TestDashboardAPI(unittest.TestCase):
    """Integration and API contract tests for dashboard endpoints."""

    def setUp(self):
        """Create a fresh app and storage for each test."""
        self.storage = MemoryStorage()
        self.tracker = Tracker(storage=self.storage)
        self.app = create_app(db_path=":memory:")
        self.app.state.service.storage = self.storage
        self.client = TestClient(self.app)

    def test_all_six_endpoints_empty_db(self):
        """Test all 6 endpoints return 200 with valid JSON even when database is empty."""
        endpoints = [
            "/api/overview",
            "/api/requests",
            "/api/fingerprints",
            "/api/models",
            "/api/analytics",
            "/api/recommendations",
        ]
        for ep in endpoints:
            response = self.client.get(ep)
            self.assertEqual(response.status_code, 200, f"Endpoint {ep} failed with status {response.status_code}")
            data = response.json()
            self.assertIsInstance(data, (dict, list))

    def test_all_six_endpoints_with_data(self):
        """Test all 6 endpoints return 200 with valid JSON when dataset contains events."""
        req1 = RequestCapture(prompt="What is EcoTrace?", provider="openai", model="gpt-4o-mini")
        res1 = ResponseCapture(response="EcoTrace is an observability SDK.", input_tokens=10, output_tokens=15, latency_ms=120.0)
        self.tracker.track(req1, res1)

        req2 = RequestCapture(prompt="What is EcoTrace?", provider="openai", model="gpt-4o-mini")
        res2 = ResponseCapture(response="EcoTrace is an observability SDK.", input_tokens=10, output_tokens=15, latency_ms=115.0)
        self.tracker.track(req2, res2)

        # Overview
        res_overview = self.client.get("/api/overview")
        self.assertEqual(res_overview.status_code, 200)
        overview_data = res_overview.json()
        self.assertEqual(overview_data["kpis"]["total_requests"], 2)
        self.assertEqual(overview_data["kpis"]["duplicate_requests"], 1)

        # Requests
        res_requests = self.client.get("/api/requests")
        self.assertEqual(res_requests.status_code, 200)
        requests_data = res_requests.json()
        self.assertEqual(requests_data["total"], 2)

        # Request Details
        req_id = requests_data["requests"][0]["request_id"]
        res_details = self.client.get(f"/api/requests/{req_id}")
        self.assertEqual(res_details.status_code, 200)

        # Fingerprints
        res_fingerprints = self.client.get("/api/fingerprints")
        self.assertEqual(res_fingerprints.status_code, 200)
        fp_data = res_fingerprints.json()
        self.assertEqual(fp_data["summary"]["unique_fingerprints"], 1)
        self.assertEqual(fp_data["summary"]["repeated_fingerprints"], 1)

        # Models
        res_models = self.client.get("/api/models")
        self.assertEqual(res_models.status_code, 200)
        models_data = res_models.json()
        self.assertEqual(models_data["total_models"], 1)

        # Analytics
        res_analytics = self.client.get("/api/analytics")
        self.assertEqual(res_analytics.status_code, 200)
        analytics_data = res_analytics.json()
        self.assertIn("timeline", analytics_data)
        self.assertIn("efficiency", analytics_data)

        # Recommendations
        res_recs = self.client.get("/api/recommendations")
        self.assertEqual(res_recs.status_code, 200)
        recs_data = res_recs.json()
        self.assertIn("recommendations", recs_data)

    def test_none_cost_compatibility_unconfigured_pricing(self):
        """Test that unconfigured model pricing returns None cost without treating it as 0 or throwing errors."""
        # CostCalculator with empty pricing table
        self.app.state.service.cost_calculator._pricing = {}

        req = RequestCapture(prompt="Custom model test", provider="custom_provider", model="unpriced-model-v1")
        res = ResponseCapture(response="Output", input_tokens=100, output_tokens=50, latency_ms=200.0)
        self.tracker.track(req, res)

        # Overview endpoint
        res_overview = self.client.get("/api/overview")
        self.assertEqual(res_overview.status_code, 200)
        data = res_overview.json()
        self.assertIsNone(data["kpis"]["estimated_cost_usd"], "Unconfigured model pricing must return null/None for total cost")

        # Requests endpoint
        res_requests = self.client.get("/api/requests")
        self.assertEqual(res_requests.status_code, 200)
        req_row = res_requests.json()["requests"][0]
        self.assertIsNone(req_row["estimated_cost_usd"])

        # Fingerprints endpoint
        res_fp = self.client.get("/api/fingerprints")
        self.assertEqual(res_fp.status_code, 200)
        fp_row = res_fp.json()["fingerprints"][0]
        self.assertIsNone(fp_row["estimated_cost_usd"])

        # Models endpoint
        res_models = self.client.get("/api/models")
        self.assertEqual(res_models.status_code, 200)
        model_row = res_models.json()["models"][0]
        self.assertIsNone(model_row["estimated_cost_usd"])

        # Analytics endpoint
        res_analytics = self.client.get("/api/analytics")
        self.assertEqual(res_analytics.status_code, 200)
        analytics_data = res_analytics.json()
        self.assertIsNone(analytics_data["timeline"]["cost"][0])

        # Recommendations endpoint
        res_recs = self.client.get("/api/recommendations")
        self.assertEqual(res_recs.status_code, 200)


if __name__ == "__main__":
    unittest.main()
