"""Duplicate request detection module.

Identifies exact duplicate AI requests using deterministic request hashing,
groups them, and quantifies wasted requests and tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ecotrace.storage.models import RequestEvent
from ecotrace.utils.hashing import hash_request


@dataclass
class DuplicateResult:
    """Result of a single duplicate detection check.

    Attributes:
        is_duplicate: Whether the request is an exact duplicate.
        duplicate_of: The request_id of the original request, if duplicate.
        occurrence_count: How many times this exact request has been seen.
    """
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    occurrence_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "is_duplicate": self.is_duplicate,
            "duplicate_of": self.duplicate_of,
            "occurrence_count": self.occurrence_count,
        }


@dataclass
class DuplicateGroup:
    """Structured representation of a group of identical requests.

    Attributes:
        request_hash: Deterministic hash of the prompt and model.
        original_request_id: Request ID of the first occurrence.
        duplicate_request_ids: Request IDs of subsequent identical calls.
        occurrence_count: Total occurrences (1 original + N duplicates).
        wasted_input_tokens: Total input tokens consumed by duplicates.
        wasted_output_tokens: Total output tokens consumed by duplicates.
        wasted_total_tokens: Total tokens consumed by duplicates.
        prompt_sample: String or message sample of the prompt.
    """
    request_hash: str
    original_request_id: str
    duplicate_request_ids: List[str] = field(default_factory=list)
    occurrence_count: int = 1
    wasted_input_tokens: int = 0
    wasted_output_tokens: int = 0
    wasted_total_tokens: int = 0
    prompt_sample: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "request_hash": self.request_hash,
            "original_request_id": self.original_request_id,
            "duplicate_request_ids": list(self.duplicate_request_ids),
            "occurrence_count": self.occurrence_count,
            "wasted_input_tokens": self.wasted_input_tokens,
            "wasted_output_tokens": self.wasted_output_tokens,
            "wasted_total_tokens": self.wasted_total_tokens,
            "prompt_sample": self.prompt_sample[:100] if self.prompt_sample else "",
        }


@dataclass
class DuplicateAnalysisResult:
    """Aggregate result of batch duplicate analysis.

    Attributes:
        total_events: Total events analyzed.
        duplicate_count: Number of duplicate requests (excluding originals).
        unique_count: Number of unique prompt/model combinations.
        wasted_input_tokens: Sum of input tokens across all duplicates.
        wasted_output_tokens: Sum of output tokens across all duplicates.
        wasted_total_tokens: Sum of total tokens across all duplicates.
        duplicate_event_ids: Set of request IDs identified as duplicates.
        duplicate_groups: List of DuplicateGroup objects for repeated prompts.
    """
    total_events: int = 0
    duplicate_count: int = 0
    unique_count: int = 0
    wasted_input_tokens: int = 0
    wasted_output_tokens: int = 0
    wasted_total_tokens: int = 0
    duplicate_event_ids: Set[str] = field(default_factory=set)
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_events": self.total_events,
            "duplicate_count": self.duplicate_count,
            "unique_count": self.unique_count,
            "wasted_input_tokens": self.wasted_input_tokens,
            "wasted_output_tokens": self.wasted_output_tokens,
            "wasted_total_tokens": self.wasted_total_tokens,
            "duplicate_event_ids": list(self.duplicate_event_ids),
            "duplicate_groups": [g.to_dict() for g in self.duplicate_groups],
        }


class DuplicateDetector:
    """Detects exact duplicate AI requests using request hashes.

    Uses the request_hash field on RequestEvent (or computes it on the fly)
    to identify and group exact duplicate requests.
    """

    def __init__(self) -> None:
        self._hash_index: Dict[str, List[str]] = {}  # hash -> [request_ids]

    def index_event(self, event: RequestEvent) -> None:
        """Add an event to the duplicate index."""
        req_hash = self._ensure_hash(event)
        if req_hash not in self._hash_index:
            self._hash_index[req_hash] = []
        self._hash_index[req_hash].append(event.request_id)

    def check(self, event: RequestEvent) -> DuplicateResult:
        """Check whether an event is a duplicate.

        Args:
            event: The RequestEvent to check.

        Returns:
            A DuplicateResult indicating whether the event is a duplicate.
        """
        req_hash = self._ensure_hash(event)
        existing = self._hash_index.get(req_hash, [])
        others = [rid for rid in existing if rid != event.request_id]

        if others:
            return DuplicateResult(
                is_duplicate=True,
                duplicate_of=others[0],
                occurrence_count=len(others) + 1,
            )
        return DuplicateResult()

    def analyze(self, events: List[RequestEvent]) -> DuplicateAnalysisResult:
        """Analyze a list of events to find all exact duplicates and waste.

        Args:
            events: List of RequestEvent objects.

        Returns:
            DuplicateAnalysisResult containing detailed duplicate statistics.
        """
        if not events:
            return DuplicateAnalysisResult()

        groups_map: Dict[str, List[RequestEvent]] = {}

        for event in events:
            if not isinstance(event, RequestEvent):
                continue
            req_hash = self._ensure_hash(event)
            if req_hash not in groups_map:
                groups_map[req_hash] = []
            groups_map[req_hash].append(event)

        duplicate_count = 0
        unique_count = len(groups_map)
        wasted_in = 0
        wasted_out = 0
        wasted_tot = 0
        duplicate_event_ids: Set[str] = set()
        group_results: List[DuplicateGroup] = []

        for req_hash, group_events in groups_map.items():
            if len(group_events) <= 1:
                continue

            original = group_events[0]
            duplicates = group_events[1:]

            group_dup_ids = [e.request_id for e in duplicates]
            duplicate_event_ids.update(group_dup_ids)

            group_wasted_in = sum(e.input_tokens for e in duplicates)
            group_wasted_out = sum(e.output_tokens for e in duplicates)
            group_wasted_tot = sum(e.total_tokens for e in duplicates)

            duplicate_count += len(duplicates)
            wasted_in += group_wasted_in
            wasted_out += group_wasted_out
            wasted_tot += group_wasted_tot

            prompt_sample = str(original.prompt) if original.prompt else ""

            group_results.append(
                DuplicateGroup(
                    request_hash=req_hash,
                    original_request_id=original.request_id,
                    duplicate_request_ids=group_dup_ids,
                    occurrence_count=len(group_events),
                    wasted_input_tokens=group_wasted_in,
                    wasted_output_tokens=group_wasted_out,
                    wasted_total_tokens=group_wasted_tot,
                    prompt_sample=prompt_sample,
                )
            )

        return DuplicateAnalysisResult(
            total_events=len(events),
            duplicate_count=duplicate_count,
            unique_count=unique_count,
            wasted_input_tokens=wasted_in,
            wasted_output_tokens=wasted_out,
            wasted_total_tokens=wasted_tot,
            duplicate_event_ids=duplicate_event_ids,
            duplicate_groups=group_results,
        )

    def get_duplicate_groups(self) -> Dict[str, List[str]]:
        """Return all groups of duplicate request IDs."""
        return {h: ids for h, ids in self._hash_index.items() if len(ids) > 1}

    def clear(self) -> None:
        """Clear the duplicate index."""
        self._hash_index.clear()

    @staticmethod
    def _ensure_hash(event: RequestEvent) -> str:
        """Ensure an event has a valid request hash."""
        if event.request_hash:
            return event.request_hash
        event.request_hash = hash_request(
            prompt=event.prompt,
            model=event.model,
            provider=event.provider,
        )
        return event.request_hash
