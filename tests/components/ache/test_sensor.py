"""Test the ache sensor platform."""

import pytest

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the ache integration for testing."""
    # Create the source sensor
    hass.states.async_set("sensor.test_temperature", "20.0")

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry


def get_ach_sensor_id(hass: HomeAssistant) -> str:
    """Get the ACH sensor entity ID."""
    states = hass.states.async_all()
    for state in states:
        if state.entity_id.startswith("sensor.ache_") and state.entity_id.endswith(
            "_ach"
        ):
            return state.entity_id
    raise ValueError("ACH sensor not found")


async def test_sensor_setup(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor is created."""
    sensor_id = get_ach_sensor_id(hass)
    state = hass.states.get(sensor_id)
    assert state is not None
    assert state.state == "20.0"


async def test_sensor_updates_with_source(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor updates when source sensor changes."""
    sensor_id = get_ach_sensor_id(hass)

    # Initial state
    state = hass.states.get(sensor_id)
    assert state.state == "20.0"

    # Update source sensor
    hass.states.async_set("sensor.test_temperature", "25.5")
    await hass.async_block_till_done()

    # Check sensor updated
    state = hass.states.get(sensor_id)
    assert state.state == "25.5"

    # Update again
    hass.states.async_set("sensor.test_temperature", "30.0")
    await hass.async_block_till_done()

    state = hass.states.get(sensor_id)
    assert state.state == "30.0"


async def test_sensor_handles_unavailable_source(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor handles unavailable source sensor."""
    sensor_id = get_ach_sensor_id(hass)

    # Set source to unavailable
    hass.states.async_set("sensor.test_temperature", "unavailable")
    await hass.async_block_till_done()

    # Sensor should still be available with last known value
    state = hass.states.get(sensor_id)
    assert state.state == "20.0"

    # Set to a new valid value
    hass.states.async_set("sensor.test_temperature", "22.0")
    await hass.async_block_till_done()

    state = hass.states.get(sensor_id)
    assert state.state == "22.0"


async def test_sensor_handles_unknown_source(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor handles unknown source sensor."""
    sensor_id = get_ach_sensor_id(hass)

    # Set source to unknown
    hass.states.async_set("sensor.test_temperature", "unknown")
    await hass.async_block_till_done()

    # Sensor should still be available with last known value
    state = hass.states.get(sensor_id)
    assert state.state == "20.0"


async def test_sensor_handles_non_numeric_source(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor handles non-numeric source values."""
    sensor_id = get_ach_sensor_id(hass)

    # Set source to non-numeric value
    hass.states.async_set("sensor.test_temperature", "not_a_number")
    await hass.async_block_till_done()

    # Sensor should still have the last valid value
    state = hass.states.get(sensor_id)
    assert state.state == "20.0"


async def test_coordinator_stores_time_series(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the coordinator stores time series data."""
    entry = init_integration
    coordinator = entry.runtime_data

    # Initial data point
    assert coordinator.data.get_count() == 1

    # Add more data points
    hass.states.async_set("sensor.test_temperature", "21.0")
    await hass.async_block_till_done()

    assert coordinator.data.get_count() == 2

    hass.states.async_set("sensor.test_temperature", "22.0")
    await hass.async_block_till_done()

    assert coordinator.data.get_count() == 3

    # Check latest value
    latest = coordinator.data.get_latest()
    assert latest is not None
    assert latest.value == 22.0


async def test_unload_entry(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test unloading the config entry."""
    entry = init_integration
    sensor_id = get_ach_sensor_id(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Sensor should be unavailable after unload
    state = hass.states.get(sensor_id)
    assert state is not None
    assert state.state == "unavailable"


async def test_coordinator_data_methods(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test coordinator data storage methods."""
    entry = init_integration
    coordinator = entry.runtime_data

    # Check get_all_data
    all_data = coordinator.data.get_all_data()
    assert len(all_data) == 1
    assert all_data[0].value == 20.0

    # Check get_count
    assert coordinator.data.get_count() == 1

    # Add more data
    hass.states.async_set("sensor.test_temperature", "21.0")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.test_temperature", "22.0")
    await hass.async_block_till_done()

    assert coordinator.data.get_count() == 3
    all_data = coordinator.data.get_all_data()
    assert len(all_data) == 3

    # Test clear
    coordinator.data.clear()
    assert coordinator.data.get_count() == 0
    assert coordinator.data.get_latest() is None
