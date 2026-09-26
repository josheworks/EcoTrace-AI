"""FastAPI web server for the EcoTrace Observability Dashboard."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ecotrace.dashboard.seed import seed_database
from ecotrace.dashboard.service import DashboardService

STATIC_DIR = Path(__file__).parent / "static"


def create_app(db_path: str = "ecotrace.db") -> FastAPI:
    """Create and configure the FastAPI application."""
    service = DashboardService(db_path=db_path)

    app = FastAPI(
        title="EcoTrace AI Observability Dashboard",
        description="Developer LLM observability and analytics platform",
        version="0.1.0",
    )
    app.state.service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static asset mounts
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
        app.mount("/ecotrace/static", StaticFiles(directory=STATIC_DIR), name="ecotrace_static")

    # Root Route: Backend information
    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Return backend and API server information."""
        return {
            "name": "EcoTrace AI",
            "status": "running",
            "health": "/health",
            "dashboard": "/ecotrace/",
            "api": "/api/",
        }

    # Health Check Route
    @app.get("/health")
    async def health() -> Dict[str, str]:
        """Health check endpoint returning system status."""
        return {"status": "healthy"}

    # Dashboard HTML routes (accessible at /ecotrace/ and /ecotrace)
    @app.get("/ecotrace", response_class=HTMLResponse)
    @app.get("/ecotrace/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        """Serve the dashboard single-page interface."""
        html_file = STATIC_DIR / "dashboard.html"
        if not html_file.exists():
            raise HTTPException(status_code=404, detail="Dashboard UI file not found")
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))

    # API endpoints router
    api_router = APIRouter()

    @api_router.get("/overview")
    async def get_overview(time_range: str = Query("all")) -> Dict[str, Any]:
        """Return KPI metrics and overview summary charts."""
        return service.get_overview(time_range=time_range)

    @api_router.get("/requests")
    async def get_requests(
        search: Optional[str] = Query(None),
        provider: Optional[str] = Query(None),
        model: Optional[str] = Query(None),
        duplicate_filter: Optional[str] = Query(None),
        time_range: str = Query("all"),
        sort_by: str = Query("timestamp"),
        sort_order: str = Query("desc"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> Dict[str, Any]:
        """Query and paginate requests with manual filtering."""
        return service.get_requests(
            search=search,
            provider=provider,
            model=model,
            duplicate_filter=duplicate_filter,
            time_range=time_range,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    @api_router.get("/requests/{request_id}")
    async def get_request_details(request_id: str) -> Dict[str, Any]:
        """Return comprehensive metadata and fingerprint history for a single request."""
        details = service.get_request_details(request_id)
        if details is None:
            raise HTTPException(status_code=404, detail="Request not found")
        return details

    @api_router.get("/fingerprints")
    async def get_fingerprints(
        search: Optional[str] = Query(None),
        provider: Optional[str] = Query(None),
        model: Optional[str] = Query(None),
        sort_by: str = Query("occurrences"),
        sort_order: str = Query("desc"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> Dict[str, Any]:
        """Aggregate and analyze request fingerprints."""
        return service.get_fingerprints(
            search=search,
            provider=provider,
            model=model,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    @api_router.get("/models")
    async def get_models() -> Dict[str, Any]:
        """Return model usage and performance metrics for manual comparison."""
        return service.get_models_comparison()

    @api_router.get("/analytics")
    async def get_analytics(time_range: str = Query("all")) -> Dict[str, Any]:
        """Return granular analytical time-series and distributions."""
        return service.get_analytics(time_range=time_range)

    @api_router.get("/recommendations")
    async def get_recommendations() -> Dict[str, Any]:
        """Return rule-based, deterministic optimization recommendations."""
        return {"recommendations": service.get_recommendations()}

    @api_router.get("/settings")
    async def get_settings() -> Dict[str, Any]:
        """Return database storage, pricing, and system details."""
        return service.get_settings_info()

    @api_router.post("/seed")
    async def seed_data() -> Dict[str, Any]:
        """Seed realistic developer sample observability events."""
        count = seed_database(db_path=db_path)
        return {"status": "success", "seeded_events": count}

    @api_router.post("/clear")
    async def clear_data() -> Dict[str, Any]:
        """Clear all stored events."""
        service.clear_database()
        return {"status": "success", "message": "Database cleared"}

    # Register API router strictly under /api
    app.include_router(api_router, prefix="/api")

    return app


def run_dashboard(
    host: str = "127.0.0.1",
    port: int = 8000,
    db_path: str = "ecotrace.db",
    auto_seed: bool = False,
) -> None:
    """Launch the dashboard web server via Uvicorn."""
    import uvicorn

    if auto_seed and not os.path.exists(db_path):
        print(f"[*] Seeding initial developer sample telemetry into '{db_path}'...")
        seed_database(db_path=db_path)

    app = create_app(db_path=db_path)
    print("============================================================")
    print(" EcoTrace AI Observability & Analytics Platform")
    print(f" Backend Info:  http://{host}:{port}/")
    print(f" Health Check:  http://{host}:{port}/health")
    print(f" Dashboard UI:  http://{host}:{port}/ecotrace/")
    print(f" API Base:      http://{host}:{port}/api/")
    print(f" Database:      {os.path.abspath(db_path)}")
    print("============================================================")
    uvicorn.run(app, host=host, port=port, log_level="info")
