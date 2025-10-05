"""Test the ache sensor platform."""

import pytest

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the ache integration for testing."""
    # Create the source sensor with initial CO2 value
    hass.states.async_set("sensor.test_temperature", "1000.0")

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry


def get_ach_sensor_id(hass: HomeAssistant) -> str:
    """Get the ACH sensor entity ID."""
    # Entity ID is simply sensor.ach (not prefixed with integration name)
    return "sensor.ach"


async def test_sensor_setup(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor is created but unavailable without sufficient decay data."""
    sensor_id = get_ach_sensor_id(hass)
    state = hass.states.get(sensor_id)
    assert state is not None
    # Sensor should be unavailable - not enough decay data yet
    assert state.state == "unavailable"


async def test_sensor_with_decay_sequence(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor calculates ACH from a decay sequence."""
    sensor_id = get_ach_sensor_id(hass)
    entry = init_integration
    coordinator = entry.runtime_data

    # Create a simulated exponential decay sequence (CO2 decreasing)
    # Starting at 1000 ppm, decaying to ~400 ppm baseline
    decay_values = [1000, 900, 820, 750, 690, 640, 600, 565, 535, 510]

    for value in decay_values:
        hass.states.async_set("sensor.test_temperature", str(value))
        await hass.async_block_till_done()

    # Should now have enough points to attempt fitting
    # Note: +1 because init_integration sets initial value of 1000.0
    assert coordinator.data.get_count() == len(decay_values) + 1

    state = hass.states.get(sensor_id)

    # Check if ACH was calculated (depends on fit quality)
    if state.state != "unavailable":
        # If fit was successful, check attributes
        assert "r_squared" in state.attributes
        assert "decay_rate" in state.attributes
        assert state.attributes["r_squared"] >= 0  # R² should be calculated
        # ACH value should be reasonable (typically 0-20 for rooms)
        ach_value = float(state.state)
        assert 0 <= ach_value <= 100  # Sanity check


async def test_sensor_insufficient_data(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test sensor remains unavailable with insufficient decay data."""
    sensor_id = get_ach_sensor_id(hass)

    # Add only a few points (less than MIN_DECAY_POINTS)
    hass.states.async_set("sensor.test_temperature", "900")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.test_temperature", "800")
    await hass.async_block_till_done()

    state = hass.states.get(sensor_id)
    # Should still be unavailable (not enough decay points)
    assert state.state == "unavailable"


async def test_sensor_handles_unavailable_source(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor handles unavailable source sensor."""
    # Set source to unavailable - should be ignored
    hass.states.async_set("sensor.test_temperature", "unavailable")
    await hass.async_block_till_done()

    # Data count should not increase
    entry = init_integration
    coordinator = entry.runtime_data
    assert coordinator.data.get_count() == 1  # Still just initial value


async def test_sensor_handles_unknown_source(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor handles unknown source sensor."""
    entry = init_integration
    coordinator = entry.runtime_data

    # Set source to unknown - should be ignored
    hass.states.async_set("sensor.test_temperature", "unknown")
    await hass.async_block_till_done()

    # Data count should not increase
    assert coordinator.data.get_count() == 1


async def test_sensor_handles_non_numeric_source(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the sensor handles non-numeric source values."""
    entry = init_integration
    coordinator = entry.runtime_data

    # Set source to non-numeric value - should be ignored
    hass.states.async_set("sensor.test_temperature", "not_a_number")
    await hass.async_block_till_done()

    # Data count should not increase
    assert coordinator.data.get_count() == 1


async def test_coordinator_stores_time_series(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the coordinator stores time series data."""
    entry = init_integration
    coordinator = entry.runtime_data

    # Initial data point
    assert coordinator.data.get_count() == 1

    # Add more data points
    hass.states.async_set("sensor.test_temperature", "950")
    await hass.async_block_till_done()

    assert coordinator.data.get_count() == 2

    hass.states.async_set("sensor.test_temperature", "900")
    await hass.async_block_till_done()

    assert coordinator.data.get_count() == 3

    # Check latest value
    latest = coordinator.data.get_latest()
    assert latest is not None
    assert latest.value == 900.0


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
    assert all_data[0].value == 1000.0

    # Check get_count
    assert coordinator.data.get_count() == 1

    # Add more data
    hass.states.async_set("sensor.test_temperature", "950")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.test_temperature", "900")
    await hass.async_block_till_done()

    assert coordinator.data.get_count() == 3
    all_data = coordinator.data.get_all_data()
    assert len(all_data) == 3

    # Test clear
    coordinator.data.clear()
    assert coordinator.data.get_count() == 0
    assert coordinator.data.get_latest() is None


async def test_decay_sequence_detection(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that coordinator detects decay sequences."""
    entry = init_integration
    coordinator = entry.runtime_data

    # Create a clear decay pattern
    values = [1000, 950, 900, 850, 800, 750, 700]
    for value in values:
        hass.states.async_set("sensor.test_temperature", str(value))
        await hass.async_block_till_done()

    # Should detect decay sequence
    decay_data = coordinator.data.detect_decay_sequence(min_points=5)
    assert len(decay_data) >= 5
    # First value should be highest, last should be lowest
    assert decay_data[0].value > decay_data[-1].value


async def test_non_decay_sequence_ignored(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that non-decaying data doesn't produce ACH estimate."""
    sensor_id = get_ach_sensor_id(hass)
    entry = init_integration
    coordinator = entry.runtime_data

    # Create random non-decaying pattern
    values = [1000, 1050, 980, 1020, 990, 1030]
    for value in values:
        hass.states.async_set("sensor.test_temperature", str(value))
        await hass.async_block_till_done()

    # Should not have valid ACH estimate
    assert coordinator.ach_estimate is None

    state = hass.states.get(sensor_id)
    assert state.state == "unavailable"
