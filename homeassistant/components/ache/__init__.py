"""The ache integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_SOURCE_SENSOR
from .coordinator import AcheCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type AcheConfigEntry = ConfigEntry[AcheCoordinator]


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
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: AcheConfigEntry) -> bool:
    """Unload a config entry."""
    # Shutdown coordinator if it was set up
    if hasattr(entry, "runtime_data") and entry.runtime_data:
        await entry.runtime_data.async_shutdown()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
