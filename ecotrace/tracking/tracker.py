"""Core tracker module."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union

from ecotrace.analysis.duplicates import DuplicateDetector
from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.storage.base import BaseStorage
from ecotrace.storage.models import RequestEvent, TrackingResult
from ecotrace.tracking.events import EventEmitter
from ecotrace.tracking.session import Session
from ecotrace.utils.hashing import hash_request
from ecotrace.utils.timestamps import utc_now


class Tracker:
    """Core tracking engine.

    Receives normalized request/response data, creates RequestEvent
    objects, and persists them through the storage backend.

    The tracker is responsible for:
        capture → normalize → store

    Advanced analysis is handled by separate modules.
    """

    def __init__(
        self,
        storage: BaseStorage,
        session: Optional[Session] = None,
    ) -> None:
        self._storage = storage
        self._session = session or Session()
        self._emitter = EventEmitter()
        self._duplicate_detector = DuplicateDetector()

    @property
    def session(self) -> Session:
        """Return the current session."""
        return self._session

    @property
    def events(self) -> EventEmitter:
        """Return the event emitter."""
        return self._emitter

    def track(
        self,
        request: RequestCapture,
        response: Optional[ResponseCapture] = None,
        latency_ms: Optional[float] = None,
    ) -> TrackingResult:
        """Track an AI request/response pair.

        Args:
            request: Normalized request data.
            response: Optional normalized response data.
            latency_ms: Optional override for latency measurement.

        Returns:
            A TrackingResult containing the persisted event.
        """
        self._emitter.emit("before_track", {"request": request.to_dict()})

        # Build the request event
        event = RequestEvent(
            provider=request.provider,
            model=request.model,
            prompt=request.prompt,
            session_id=self._session.session_id,
            timestamp=utc_now(),
            request_hash=hash_request(
                prompt=request.prompt,
                model=request.model,
                provider=request.provider,
            ),
            metadata=request.metadata,
        )

        # Merge response data if available
        if response is not None:
            event.response = response.response
            event.input_tokens = response.input_tokens
            event.output_tokens = response.output_tokens
            event.total_tokens = response.total_tokens
            event.latency_ms = latency_ms if latency_ms is not None else response.latency_ms

        # Check duplicate status
        dup_check = self._duplicate_detector.check(event)
        self._duplicate_detector.index_event(event)

        # Persist
        self._storage.save_event(event)
        self._session.increment()

        result = TrackingResult(
            event=event,
            is_duplicate=dup_check.is_duplicate,
            duplicate_count=dup_check.occurrence_count - 1 if dup_check.is_duplicate else 0,
        )

        self._emitter.emit("after_track", {"result": result.to_dict()})

        return result

    def get_event(self, request_id: str) -> Optional[RequestEvent]:
        """Retrieve an event by ID."""
        return self._storage.get_event(request_id)

    def get_events(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> List[RequestEvent]:
        """Retrieve tracked events."""
        return self._storage.get_events(
            session_id=self._session.session_id,
            provider=provider,
            model=model,
            limit=limit,
        )

    def count(self) -> int:
        """Count events in the current session."""
        return self._storage.count_events(session_id=self._session.session_id)
