"""The ache integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_MIN_R_SQUARED,
    CONF_ROOM_VOLUME,
    CONF_SOURCE_SENSOR,
    DEFAULT_MIN_R_SQUARED,
    DOMAIN,
)
from .coordinator import AcheCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

ACHE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOURCE_SENSOR): cv.entity_id,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_ROOM_VOLUME, default=50.0): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=1000.0)
        ),
        vol.Optional(CONF_MIN_R_SQUARED, default=DEFAULT_MIN_R_SQUARED): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=1.0)
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [ACHE_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)

type AcheConfigEntry = ConfigEntry[AcheCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the ache component from YAML configuration."""
    if DOMAIN not in config:
        return True

    for conf in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=conf,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: AcheConfigEntry) -> bool:
    """Set up ache from a config entry."""
    source_entity_id = entry.data[CONF_SOURCE_SENSOR]

    # Verify source sensor exists before setting up
    if not hass.states.get(source_entity_id):
        raise ConfigEntryNotReady(
            f"Source sensor {source_entity_id} not found. "
            "Please ensure the sensor is available before setting up this integration."
        )

    coordinator = AcheCoordinator(hass, source_entity_id, entry)
    await coordinator.async_setup()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: AcheConfigEntry) -> bool:
    """Unload a config entry."""
    # Shutdown coordinator if it was set up
    if hasattr(entry, "runtime_data") and entry.runtime_data:
        await entry.runtime_data.async_shutdown()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
