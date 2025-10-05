"""Data update coordinator for the ache integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_BASELINE_CO2,
    CONF_MIN_R_SQUARED,
    CONF_ROOM_VOLUME,
    MIN_DECAY_POINTS,
)
from .models import AchEstimate, TimeSeriesData

if TYPE_CHECKING:
    from . import AcheConfigEntry

_LOGGER = logging.getLogger(__name__)


class AcheCoordinator(DataUpdateCoordinator[TimeSeriesData]):
    """Coordinator to manage ache time series data."""

    config_entry: AcheConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        source_entity_id: str,
        config_entry: AcheConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="ACH Coordinator",
            config_entry=config_entry,
        )
        self.source_entity_id = source_entity_id
        self.data = TimeSeriesData()
        self._unsubscribe: CALLBACK_TYPE | None = None

        # Configuration
        self.room_volume = config_entry.data[CONF_ROOM_VOLUME]
        self.min_r_squared = config_entry.data[CONF_MIN_R_SQUARED]
        self.baseline_co2 = config_entry.data.get(
            CONF_BASELINE_CO2, 420.0
        )  # Default for older configs

        # ACH calculation results
        self.ach_estimate: AchEstimate | None = None

    async def _async_update_data(self) -> TimeSeriesData:
        """Update data via polling (not used - event-driven coordinator).

        This coordinator is event-driven and updates via state change events.
        This method is implemented to satisfy DataUpdateCoordinator requirements
        but doesn't perform any actual updates.
        """
        return self.data

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Process initial state if available
        if (state := self.hass.states.get(self.source_entity_id)) is not None:
            self._process_state(state)

        # Subscribe to state changes
        self._unsubscribe = async_track_state_change_event(
            self.hass, self.source_entity_id, self._handle_state_change
        )

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle state changes of the source sensor."""
        new_state = event.data["new_state"]
        if new_state is not None:
            self._process_state(new_state)
            # Try to calculate ACH estimate after each update
            self._calculate_ach()
            self.async_set_updated_data(self.data)

    def _process_state(self, state: State) -> None:
        """Process a state and add to time series if valid."""
        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug(
                "Source sensor %s is %s, skipping data point",
                self.source_entity_id,
                state.state,
            )
            return

        try:
            value = float(state.state)
            timestamp = state.last_updated or datetime.now()
            self.data.add_data_point(timestamp, value)
            _LOGGER.debug(
                "Added data point: %s = %s (total: %s points)",
                timestamp,
                value,
                self.data.get_count(),
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "Could not convert state to float for %s: %s (state: %s)",
                self.source_entity_id,
                err,
                state.state,
            )

    def _calculate_ach(self) -> None:
        """Calculate ACH estimate from time series data."""
        estimate = self.data.fit_exponential_decay(
            self.room_volume,
            min_points=MIN_DECAY_POINTS,
            min_r_squared=self.min_r_squared,
            baseline_co2=self.baseline_co2,
        )

        if estimate is not None:
            self.ach_estimate = estimate
            _LOGGER.info(
                "ACH estimate: %.2f changes/hour (R²=%.4f, decay_rate=%.6f/s)",
                estimate.ach,
                estimate.r_squared,
                estimate.decay_rate,
            )
        else:
            self.ach_estimate = None

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
