"""Duplicate request detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from ecotrace.storage.models import RequestEvent


@dataclass
class DuplicateResult:
    """Result of a duplicate detection check.

    Attributes:
        is_duplicate: Whether the request is an exact duplicate.
        duplicate_of: The request_id of the original request, if duplicate.
        occurrence_count: How many times this exact request has been seen.
    """
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    occurrence_count: int = 1


class DuplicateDetector:
    """Detects exact duplicate AI requests using request hashes.

    Uses the request_hash field on RequestEvent to identify duplicates.
    """

    def __init__(self) -> None:
        self._hash_index: Dict[str, List[str]] = {}  # hash -> [request_ids]

    def index_event(self, event: RequestEvent) -> None:
        """Add an event to the duplicate index."""
        if event.request_hash is None:
            return
        if event.request_hash not in self._hash_index:
            self._hash_index[event.request_hash] = []
        self._hash_index[event.request_hash].append(event.request_id)

    def check(self, event: RequestEvent) -> DuplicateResult:
        """Check whether an event is a duplicate.

        Args:
            event: The RequestEvent to check.

        Returns:
            A DuplicateResult indicating whether the event is a duplicate.
        """
        if event.request_hash is None:
            return DuplicateResult()

        existing = self._hash_index.get(event.request_hash, [])
        # Filter out the event itself
        others = [rid for rid in existing if rid != event.request_id]

        if others:
            return DuplicateResult(
                is_duplicate=True,
                duplicate_of=others[0],
                occurrence_count=len(others) + 1,
            )
        return DuplicateResult()

    def get_duplicate_groups(self) -> Dict[str, List[str]]:
        """Return all groups of duplicate request IDs.

        Returns:
            Dict mapping request_hash to list of request_ids with count > 1.
        """
        return {
            h: ids for h, ids in self._hash_index.items() if len(ids) > 1
        }

    def clear(self) -> None:
        """Clear the duplicate index."""
        self._hash_index.clear()
