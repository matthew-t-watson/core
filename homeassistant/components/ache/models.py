"""Models for the ache integration."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import AcheCoordinator


@dataclass
class TimeSeriesDataPoint:
    """Represent a single data point in the time series."""

    timestamp: datetime
    value: float


class TimeSeriesData:
    """Store and manage time series data for statistical analysis."""

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize the time series data storage."""
        self._max_size = max_size
        self._data: deque[TimeSeriesDataPoint] = deque(maxlen=max_size)

    def add_data_point(self, timestamp: datetime, value: float) -> None:
        """Add a new data point to the time series."""
        self._data.append(TimeSeriesDataPoint(timestamp=timestamp, value=value))

    def get_latest(self) -> TimeSeriesDataPoint | None:
        """Get the most recent data point."""
        if self._data:
            return self._data[-1]
        return None

    def get_all_data(self) -> list[TimeSeriesDataPoint]:
        """Get all stored data points."""
        return list(self._data)

    def get_count(self) -> int:
        """Get the number of data points stored."""
        return len(self._data)

    def clear(self) -> None:
        """Clear all stored data."""
        self._data.clear()


type AcheConfigEntry = ConfigEntry[AcheCoordinator]
