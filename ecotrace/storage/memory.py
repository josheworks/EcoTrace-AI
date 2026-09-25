"""In-memory storage backend."""

from __future__ import annotations

from typing import Dict, List, Optional

from ecotrace.storage.base import BaseStorage
from ecotrace.storage.models import RequestEvent


class MemoryStorage(BaseStorage):
    """In-memory storage backend for testing and lightweight usage.

    Events are stored in a plain dict keyed by request_id.
    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        self._events: Dict[str, RequestEvent] = {}

    def save_event(self, event: RequestEvent) -> None:
        """Store an event in memory."""
        self._events[event.request_id] = event

    def get_event(self, request_id: str) -> Optional[RequestEvent]:
        """Retrieve an event by request ID."""
        return self._events.get(request_id)

    def get_events(
        self,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RequestEvent]:
        """Filter and paginate in-memory events."""
        results = list(self._events.values())

        if session_id is not None:
            results = [e for e in results if e.session_id == session_id]
        if provider is not None:
            results = [e for e in results if e.provider == provider]
        if model is not None:
            results = [e for e in results if e.model == model]

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results[offset : offset + limit]

    def count_events(
        self,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> int:
        """Count events matching optional filters."""
        count = 0
        for event in self._events.values():
            if session_id is not None and event.session_id != session_id:
                continue
            if provider is not None and event.provider != provider:
                continue
            if model is not None and event.model != model:
                continue
            count += 1
        return count

    def clear(self) -> None:
        """Clear all stored events."""
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)
