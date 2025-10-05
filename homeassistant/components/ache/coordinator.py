"""Data update coordinator for the ache integration."""

from __future__ import annotations

from datetime import datetime, timedelta
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

from .models import TimeSeriesData

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
            update_interval=timedelta(seconds=30),
            config_entry=config_entry,
        )
        self.source_entity_id = source_entity_id
        self.data = TimeSeriesData()
        self._unsubscribe: CALLBACK_TYPE | None = None

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

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
