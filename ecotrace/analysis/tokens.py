"""Token usage analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ecotrace.storage.models import RequestEvent


@dataclass
class TokenStats:
    """Aggregate token usage statistics.

    Attributes:
        total_input_tokens: Sum of all input tokens.
        total_output_tokens: Sum of all output tokens.
        total_tokens: Sum of all tokens.
        avg_input_tokens: Average input tokens per request.
        avg_output_tokens: Average output tokens per request.
        avg_total_tokens: Average total tokens per request.
        max_input_tokens: Maximum input tokens in a single request.
        max_output_tokens: Maximum output tokens in a single request.
        request_count: Number of requests analyzed.
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    avg_total_tokens: float = 0.0
    max_input_tokens: int = 0
    max_output_tokens: int = 0
    request_count: int = 0


class TokenAnalyzer:
    """Analyzes token usage across tracked events."""

    def analyze(self, events: List[RequestEvent]) -> TokenStats:
        """Compute aggregate token statistics.

        Args:
            events: List of RequestEvent objects.

        Returns:
            TokenStats with computed aggregates.
        """
        if not events:
            return TokenStats()

        total_in = sum(e.input_tokens for e in events)
        total_out = sum(e.output_tokens for e in events)
        total = sum(e.total_tokens for e in events)
        n = len(events)

        return TokenStats(
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_tokens=total,
            avg_input_tokens=total_in / n,
            avg_output_tokens=total_out / n,
            avg_total_tokens=total / n,
            max_input_tokens=max(e.input_tokens for e in events),
            max_output_tokens=max(e.output_tokens for e in events),
            request_count=n,
        )
