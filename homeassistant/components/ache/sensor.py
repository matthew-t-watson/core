"""Sensor platform for the ache integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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


class AcheSensor(CoordinatorEntity[AcheCoordinator], SensorEntity):
    """Sensor that displays the ACH estimate."""

    _attr_has_entity_name = True
    _attr_translation_key = "ach"
    _attr_should_poll = False
    _attr_native_unit_of_measurement = "ACH"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: AcheCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_ach"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Coordinator must be available AND we must have a valid ACH estimate
        return super().available and self.coordinator.ach_estimate is not None

    @property
    def extra_state_attributes(self) -> dict[str, float | int]:
        """Return extra state attributes."""
        estimate = self.coordinator.ach_estimate

        if estimate is not None:
            return {
                "r_squared": round(estimate.r_squared, 4),
                "decay_rate": round(estimate.decay_rate, 6),
                "baseline_ppm": round(estimate.baseline, 1),
                "initial_ppm": round(estimate.initial_value, 1),
                "data_points": self.coordinator.data.get_count(),
                "room_volume_m3": self.coordinator.room_volume,
            }

        # No valid ACH estimate - return basic diagnostic info
        return {
            "data_points": self.coordinator.data.get_count(),
            "room_volume_m3": self.coordinator.room_volume,
            "min_r_squared_threshold": self.coordinator.min_r_squared,
        }

    def _update_from_coordinator(self) -> None:
        """Update sensor state from coordinator data."""
        estimate = self.coordinator.ach_estimate

        if estimate is not None:
            self._attr_native_value = round(estimate.ach, 2)
        else:
            # No valid ACH estimate available
            self._attr_native_value = None

        _LOGGER.debug(
            "Updated sensor state: ACH=%s, available=%s, data_points=%d",
            self._attr_native_value,
            self.available,
            self.coordinator.data.get_count(),
        )
