"""Models for the ache integration."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import TYPE_CHECKING

import numpy as np
from scipy import optimize

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import AcheCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class TimeSeriesDataPoint:
    """Represent a single data point in the time series."""

    timestamp: datetime
    value: float


@dataclass
class AchEstimate:
    """Represent an ACH estimate with quality metrics."""

    ach: float  # Air changes per hour
    r_squared: float  # R² goodness of fit
    decay_rate: float  # Decay constant (λ)
    baseline: float  # Baseline CO2 level
    initial_value: float  # Initial CO2 level


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

    def detect_decay_sequence(self, min_points: int = 5) -> list[TimeSeriesDataPoint]:
        """Detect a monotonically decreasing sequence in the data.

        Returns the longest recent sequence of decreasing values,
        or empty list if no valid sequence found.
        """
        if len(self._data) < min_points:
            return []

        decay_sequence: list[TimeSeriesDataPoint] = []

        # Iterate backwards to find most recent decay
        for i in range(len(self._data) - 1, -1, -1):
            current_point = self._data[i]

            if not decay_sequence:
                # Start a new sequence
                decay_sequence.append(current_point)
            elif current_point.value > decay_sequence[-1].value:
                # Value is decreasing (going backwards in time)
                decay_sequence.append(current_point)
            else:
                # Sequence broken
                break

        # Reverse to get chronological order
        decay_sequence.reverse()

        if len(decay_sequence) >= min_points:
            return decay_sequence
        return []

    def fit_exponential_decay(
        self,
        room_volume_m3: float,
        min_points: int = 5,
        min_r_squared: float = 0.85,
        baseline_co2: float = 420.0,
    ) -> AchEstimate | None:
        """Fit exponential decay model to data and calculate ACH.

        Uses an iterative approach: starts with recent data and expands backwards
        in time, continuing as long as R² remains above threshold. This is robust
        to noisy sensor data.

        The exponential decay model is:
        C(t) = C_baseline + (C_0 - C_baseline) * e^(-λt)

        Where:
        - C(t) is concentration at time t
        - C_baseline is the baseline (outdoor) concentration
        - C_0 is the initial concentration
        - λ is the decay rate constant
        - ACH = λ * 3600 (convert from per-second to per-hour)

        Args:
            room_volume_m3: Room volume in cubic meters
            min_points: Minimum number of points needed for fitting
            min_r_squared: Minimum R² quality threshold
            baseline_co2: Baseline CO2 level in ppm (outdoor air, typically 420)

        Returns:
            AchEstimate if successful fit with good quality, None otherwise
        """
        if len(self._data) < min_points:
            _LOGGER.debug(
                "Not enough data points: %d (need %d)", len(self._data), min_points
            )
            return None

        # Define exponential decay function
        def exp_decay(
            t: np.ndarray, baseline: float, amplitude: float, decay_rate: float
        ) -> np.ndarray:
            """Exponential decay: C(t) = baseline + amplitude * e^(-decay_rate * t)."""
            return baseline + amplitude * np.exp(-decay_rate * t)

        best_estimate: AchEstimate | None = None
        best_window_size = 0

        # Try increasingly larger windows of recent data
        for window_size in range(min_points, len(self._data) + 1):
            # Get the most recent window_size points
            window_data = list(self._data)[-window_size:]

            # Convert to numpy arrays
            times = np.array(
                [
                    (point.timestamp - window_data[0].timestamp).total_seconds()
                    for point in window_data
                ]
            )
            concentrations = np.array([point.value for point in window_data])

            # Check if data is generally decreasing (simple sanity check)
            if concentrations[0] <= concentrations[-1]:
                # Not a decay - values increasing or flat
                _LOGGER.debug(
                    "Window size %d: Not a decay sequence (start=%.1f, end=%.1f)",
                    window_size,
                    concentrations[0],
                    concentrations[-1],
                )
                break

            try:
                # Initial parameter guesses
                # Use configured baseline as starting point
                baseline_guess = baseline_co2
                amplitude_guess = concentrations[0] - baseline_guess
                half_time = times[-1] / 2
                decay_rate_guess = np.log(2) / half_time if half_time > 0 else 0.001

                # Fit the curve
                popt, _ = optimize.curve_fit(
                    exp_decay,
                    times,
                    concentrations,
                    p0=[baseline_guess, amplitude_guess, decay_rate_guess],
                    bounds=(
                        [0, 0, 0],  # Lower bounds
                        [np.inf, np.inf, 10],  # Upper bounds
                    ),
                    maxfev=5000,
                )

                baseline, amplitude, decay_rate = popt

                # Calculate R²
                predicted = exp_decay(times, baseline, amplitude, decay_rate)
                residuals = concentrations - predicted
                ss_res = np.sum(residuals**2)
                ss_tot = np.sum((concentrations - np.mean(concentrations)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                _LOGGER.debug(
                    "Window size %d: R²=%.4f, ACH=%.2f, decay_rate=%.6f",
                    window_size,
                    r_squared,
                    decay_rate * 3600,
                    decay_rate,
                )

                # If R² meets threshold, this is a valid estimate
                if r_squared >= min_r_squared:
                    # Convert decay rate to ACH (per hour)
                    ach = decay_rate * 3600

                    best_estimate = AchEstimate(
                        ach=ach,
                        r_squared=r_squared,
                        decay_rate=decay_rate,
                        baseline=baseline,
                        initial_value=baseline + amplitude,
                    )
                    best_window_size = window_size
                else:
                    # R² fell below threshold, stop expanding
                    _LOGGER.debug(
                        "Window size %d: R²=%.4f below threshold %.4f, stopping",
                        window_size,
                        r_squared,
                        min_r_squared,
                    )
                    break

            except (RuntimeError, ValueError, optimize.OptimizeWarning) as err:
                _LOGGER.debug("Window size %d: Fit failed: %s", window_size, err)
                break

        if best_estimate:
            _LOGGER.info(
                "Best fit using %d points: ACH=%.2f, R²=%.4f, decay_rate=%.6f/s",
                best_window_size,
                best_estimate.ach,
                best_estimate.r_squared,
                best_estimate.decay_rate,
            )
        else:
            _LOGGER.debug("No valid exponential decay fit found")

        return best_estimate


type AcheConfigEntry = ConfigEntry[AcheCoordinator]
