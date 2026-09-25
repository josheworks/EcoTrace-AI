"""Carbon footprint estimation.

NOTE: Carbon estimates are rough approximations. Actual carbon impact
depends on the energy grid, provider, and region. More accurate models
will be implemented in future phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ecotrace.impact.energy import EnergyEstimator, EnergyEstimate
from ecotrace.storage.models import RequestEvent


# Global average grid intensity: gCO2/kWh (approximate)
_DEFAULT_GRID_INTENSITY = 475.0


@dataclass
class CarbonEstimate:
    """Carbon footprint estimation result.

    Attributes:
        total_gco2: Total estimated CO2 in grams.
        total_kgco2: Total estimated CO2 in kilograms.
        grid_intensity_gco2_kwh: Grid carbon intensity used.
        energy_kwh: Energy consumption used for calculation.
        request_count: Number of requests.
    """
    total_gco2: float = 0.0
    total_kgco2: float = 0.0
    grid_intensity_gco2_kwh: float = _DEFAULT_GRID_INTENSITY
    energy_kwh: float = 0.0
    request_count: int = 0


class CarbonEstimator:
    """Estimates carbon footprint of AI workloads.

    Combines energy estimates with grid carbon intensity.
    This is a placeholder; real models will be plugged in later.
    """

    def __init__(
        self,
        grid_intensity: float = _DEFAULT_GRID_INTENSITY,
        energy_estimator: EnergyEstimator | None = None,
    ) -> None:
        self._grid_intensity = grid_intensity
        self._energy = energy_estimator or EnergyEstimator()

    def estimate(self, events: List[RequestEvent]) -> CarbonEstimate:
        """Estimate carbon footprint for a list of events."""
        energy = self._energy.estimate(events)
        gco2 = energy.total_kwh * self._grid_intensity

        return CarbonEstimate(
            total_gco2=round(gco2, 6),
            total_kgco2=round(gco2 / 1000, 9),
            grid_intensity_gco2_kwh=self._grid_intensity,
            energy_kwh=energy.total_kwh,
            request_count=len(events),
        )
