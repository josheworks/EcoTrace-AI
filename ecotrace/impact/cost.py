"""Cost estimation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ecotrace.storage.models import RequestEvent


# Default pricing per 1K tokens (USD) — illustrative only
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
}


@dataclass
class CostEstimate:
    """Cost estimation result.

    Attributes:
        total_cost_usd: Total estimated cost in USD.
        input_cost_usd: Cost for input tokens.
        output_cost_usd: Cost for output tokens.
        currency: Currency code.
        model: Model used for estimation.
        request_count: Number of requests.
    """
    total_cost_usd: float = 0.0
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    currency: str = "USD"
    model: str = ""
    request_count: int = 0


class CostCalculator:
    """Estimates monetary cost of AI workloads.

    Uses configurable per-model pricing tables.
    """

    def __init__(
        self, pricing: Optional[Dict[str, Dict[str, float]]] = None
    ) -> None:
        self._pricing = pricing or dict(_DEFAULT_PRICING)

    def set_pricing(
        self, model: str, input_per_1k: float, output_per_1k: float
    ) -> None:
        """Set or update pricing for a model."""
        self._pricing[model] = {"input": input_per_1k, "output": output_per_1k}

    def estimate(self, events: List[RequestEvent]) -> CostEstimate:
        """Estimate total cost for a list of events.

        Args:
            events: List of RequestEvent objects.

        Returns:
            CostEstimate with computed costs.
        """
        total_input = 0.0
        total_output = 0.0

        for event in events:
            pricing = self._pricing.get(event.model, {})
            input_rate = pricing.get("input", 0.0)
            output_rate = pricing.get("output", 0.0)

            total_input += (event.input_tokens / 1000) * input_rate
            total_output += (event.output_tokens / 1000) * output_rate

        return CostEstimate(
            total_cost_usd=round(total_input + total_output, 6),
            input_cost_usd=round(total_input, 6),
            output_cost_usd=round(total_output, 6),
            request_count=len(events),
        )
