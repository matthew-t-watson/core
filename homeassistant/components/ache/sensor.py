"""Sensor platform for the ache integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AcheCoordinator
from .models import AcheConfigEntry

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AcheConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ACH sensor from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities([AcheSensor(coordinator, entry.entry_id)])


class AcheSensor(SensorEntity):
    """Sensor that displays the latest value from the time series."""

    _attr_has_entity_name = True
    _attr_translation_key = "ach"
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AcheCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry_id}_ach"

        # Subscribe to coordinator updates
        self.async_on_remove(
            coordinator.async_add_listener(self._handle_coordinator_update)
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Update with current data
        self._update_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        self.async_write_ha_state()

    def _update_from_coordinator(self) -> None:
        """Update sensor state from coordinator data."""
        latest = self.coordinator.data.get_latest()
        if latest is not None:
            self._attr_native_value = latest.value
            self._attr_available = True
        else:
            self._attr_native_value = None
            self._attr_available = False

        _LOGGER.debug(
            "Updated sensor state: value=%s, count=%d",
            self._attr_native_value,
            self.coordinator.data.get_count(),
        )
