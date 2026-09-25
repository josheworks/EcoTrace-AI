"""Unit tests for the EcoTrace Dashboard service and API endpoints."""

import os
import tempfile
import unittest

from ecotrace.dashboard.app import create_app
from ecotrace.dashboard.seed import seed_database
from ecotrace.dashboard.service import DashboardService
from ecotrace.storage.memory import MemoryStorage
from ecotrace.storage.models import RequestEvent
from ecotrace.storage.sqlite import SQLiteStorage
from starlette.testclient import TestClient


class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_dashboard_service_empty(self):
        """Test DashboardService when storage has 0 events."""
        storage = SQLiteStorage(db_path=self.db_path)
        service = DashboardService(storage=storage, db_path=self.db_path)

        overview = service.get_overview()
        self.assertEqual(overview["kpis"]["total_requests"], 0)
        self.assertEqual(overview["kpis"]["duplicate_requests"], 0)
        self.assertEqual(overview["kpis"]["ecoscore"]["score"], 100.0)

        requests = service.get_requests()
        self.assertEqual(requests["total"], 0)
        self.assertEqual(len(requests["requests"]), 0)

        fingerprints = service.get_fingerprints()
        self.assertEqual(fingerprints["total"], 0)

        models = service.get_models_comparison()
        self.assertEqual(models["total_models"], 0)

        analytics = service.get_analytics()
        self.assertEqual(len(analytics["timeline"]["labels"]), 0)

        recs = service.get_recommendations()
        self.assertEqual(len(recs), 0)

        settings = service.get_settings_info()
        self.assertEqual(settings["storage"]["total_events"], 0)
        service.close()
        storage.close()

    def test_dashboard_service_with_seeded_data(self):
        """Test DashboardService with populated sample data."""
        count = seed_database(db_path=self.db_path)
        self.assertGreater(count, 0)

        service = DashboardService(db_path=self.db_path)

        # Overview
        overview = service.get_overview()
        self.assertEqual(overview["kpis"]["total_requests"], count)
        self.assertGreater(overview["kpis"]["total_tokens"], 0)
        self.assertGreater(overview["kpis"]["duplicate_requests"], 0)
        self.assertGreater(overview["kpis"]["estimated_cost_usd"], 0)

        # Requests
        reqs = service.get_requests(limit=10)
        self.assertEqual(reqs["total"], count)
        self.assertEqual(len(reqs["requests"]), 10)
        first_req_id = reqs["requests"][0]["request_id"]

        # Request Details
        details = service.get_request_details(first_req_id)
        self.assertIsNotNone(details)
        self.assertIn("basic", details)
        self.assertIn("fingerprint", details)
        self.assertIn("usage", details)
        self.assertIn("duplicate_status", details)

        # Fingerprints
        fps = service.get_fingerprints()
        self.assertGreater(fps["total"], 0)
        self.assertGreater(fps["summary"]["repeated_fingerprints"], 0)
        self.assertGreater(fps["summary"]["potential_savings_tokens"], 0)

        # Models
        models = service.get_models_comparison()
        self.assertGreater(models["total_models"], 0)

        # Analytics
        analytics = service.get_analytics()
        self.assertIn("timeline", analytics)
        self.assertIn("efficiency", analytics)
        self.assertIn("providers", analytics)

        # Recommendations
        recs = service.get_recommendations()
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)
        # Verify structure of each recommendation
        for r in recs:
            self.assertIn("observation", r)
            self.assertIn("evidence", r)
            self.assertIn("suggested_action", r)
            self.assertIn("expected_impact", r)
            self.assertIn("confidence", r)

        service.close()

    def test_fastapi_endpoints(self):
        """Test FastAPI HTTP endpoints using Starlette TestClient."""
        seed_database(db_path=self.db_path)
        app = create_app(db_path=self.db_path)
        client = TestClient(app)

        try:
            # Root route: backend server information
            res = client.get("/")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["name"], "EcoTrace AI")
            self.assertEqual(data["status"], "running")
            self.assertEqual(data["health"], "/health")
            self.assertEqual(data["dashboard"], "/ecotrace/")
            self.assertEqual(data["api"], "/api/")

            # Health check route
            res = client.get("/health")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"status": "healthy"})

            # Dashboard routes: serves complete dashboard HTML
            res_slash = client.get("/ecotrace/")
            self.assertEqual(res_slash.status_code, 200)
            self.assertIn("EcoTrace AI", res_slash.text)
            self.assertIn("LLM Observability & Efficiency", res_slash.text)

            res_noslash = client.get("/ecotrace")
            self.assertEqual(res_noslash.status_code, 200)
            self.assertIn("EcoTrace AI", res_noslash.text)

            # Confirm /ecotrace/api is not used / returns 404
            self.assertEqual(client.get("/ecotrace/api/overview").status_code, 404)

            # API Overview
            res = client.get("/api/overview")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("kpis", data)
            self.assertIn("activity_chart", data)

            # API Requests
            res = client.get("/api/requests?limit=5")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(len(data["requests"]), 5)

            # API Single Request Details
            first_req_id = data["requests"][0]["request_id"]
            res = client.get(f"/api/requests/{first_req_id}")
            self.assertEqual(res.status_code, 200)
            req_detail = res.json()
            self.assertIn("basic", req_detail)
            self.assertIn("fingerprint", req_detail)

            # API Fingerprints
            res = client.get("/api/fingerprints")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("fingerprints", data)

            # API Models
            res = client.get("/api/models")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("models", data)

            # API Analytics
            res = client.get("/api/analytics")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("timeline", data)

            # API Recommendations
            res = client.get("/api/recommendations")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("recommendations", data)

            # API Settings
            res = client.get("/api/settings")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("storage", data)

            # API Seed
            res = client.post("/api/seed")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], "success")

            # API Clear
            res = client.post("/api/clear")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], "success")
        finally:
            app.state.service.close()



if __name__ == "__main__":
    unittest.main()
