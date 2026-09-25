"""Energy consumption estimation.

NOTE: Energy estimates are rough approximations. Actual energy consumption
depends on hardware, data center, and provider infrastructure.
More accurate models will be implemented in future phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ecotrace.storage.models import RequestEvent


# Rough estimate: Wh per 1K tokens (illustrative, not scientifically precise)
_DEFAULT_WH_PER_1K_TOKENS = 0.01


@dataclass
class EnergyEstimate:
    """Energy estimation result.

    Attributes:
        total_wh: Total estimated energy in watt-hours.
        total_kwh: Total estimated energy in kilowatt-hours.
        wh_per_1k_tokens: Rate used for estimation.
        total_tokens: Total tokens processed.
        request_count: Number of requests.
    """
    total_wh: float = 0.0
    total_kwh: float = 0.0
    wh_per_1k_tokens: float = _DEFAULT_WH_PER_1K_TOKENS
    total_tokens: int = 0
    request_count: int = 0

    def to_dict(self) -> dict:
        """Serialize energy estimate to dictionary."""
        return {
            "total_wh": round(self.total_wh, 4),
            "total_kwh": round(self.total_kwh, 6),
            "wh_per_1k_tokens": self.wh_per_1k_tokens,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
        }



class EnergyEstimator:
    """Estimates energy consumption of AI workloads.

    Uses a configurable watt-hours per 1K tokens rate.
    This is a placeholder; real estimation models will be plugged in later.
    """

    def __init__(self, wh_per_1k_tokens: float = _DEFAULT_WH_PER_1K_TOKENS) -> None:
        self._rate = wh_per_1k_tokens

    def estimate(self, events: List[RequestEvent]) -> EnergyEstimate:
        """Estimate energy for a list of events."""
        total_tokens = sum(e.total_tokens for e in events)
        wh = (total_tokens / 1000) * self._rate

        return EnergyEstimate(
            total_wh=round(wh, 6),
            total_kwh=round(wh / 1000, 9),
            wh_per_1k_tokens=self._rate,
            total_tokens=total_tokens,
            request_count=len(events),
        )
