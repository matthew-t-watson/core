"""Test the ache YAML configuration."""

import pytest

from homeassistant.components.ache.const import (
    CONF_MIN_R_SQUARED,
    CONF_ROOM_VOLUME,
    CONF_SOURCE_SENSOR,
    DEFAULT_MIN_R_SQUARED,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
async def setup_source_sensor(hass: HomeAssistant) -> None:
    """Create source sensor for tests."""
    hass.states.async_set("sensor.test_co2", "1000")


async def test_yaml_single_entry(hass: HomeAssistant) -> None:
    """Test YAML configuration with single entry."""
    config = {
        DOMAIN: [
            {
                CONF_SOURCE_SENSOR: "sensor.test_co2",
                CONF_ROOM_VOLUME: 50.0,
                CONF_MIN_R_SQUARED: 0.85,
            }
        ]
    }

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    # Check that a config entry was created
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data[CONF_SOURCE_SENSOR] == "sensor.test_co2"
    assert entries[0].data[CONF_ROOM_VOLUME] == 50.0
    assert entries[0].data[CONF_MIN_R_SQUARED] == 0.85


async def test_yaml_multiple_entries(hass: HomeAssistant) -> None:
    """Test YAML configuration with multiple entries."""
    hass.states.async_set("sensor.bedroom_co2", "800")

    config = {
        DOMAIN: [
            {
                CONF_SOURCE_SENSOR: "sensor.test_co2",
                CONF_ROOM_VOLUME: 50.0,
            },
            {
                CONF_SOURCE_SENSOR: "sensor.bedroom_co2",
                CONF_ROOM_VOLUME: 35.0,
                CONF_MIN_R_SQUARED: 0.9,
            },
        ]
    }

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    # Check that both config entries were created
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2


async def test_yaml_with_defaults(hass: HomeAssistant) -> None:
    """Test YAML configuration uses default values."""
    config = {
        DOMAIN: [
            {
                CONF_SOURCE_SENSOR: "sensor.test_co2",
                CONF_ROOM_VOLUME: 50.0,
                # min_r_squared not specified, should use default
            }
        ]
    }

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    # Should use default value
    assert entries[0].data[CONF_MIN_R_SQUARED] == DEFAULT_MIN_R_SQUARED


async def test_yaml_no_config(hass: HomeAssistant) -> None:
    """Test setup without YAML configuration."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    # No entries should be created
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 0


async def test_yaml_duplicate_sensor_ignored(hass: HomeAssistant) -> None:
    """Test that duplicate sensor configurations are ignored."""
    config = {
        DOMAIN: [
            {
                CONF_SOURCE_SENSOR: "sensor.test_co2",
                CONF_ROOM_VOLUME: 50.0,
            },
            {
                CONF_SOURCE_SENSOR: "sensor.test_co2",  # Duplicate
                CONF_ROOM_VOLUME: 60.0,
            },
        ]
    }

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    # Only one entry should be created (duplicate is ignored)
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data[CONF_SOURCE_SENSOR] == "sensor.test_co2"


async def test_yaml_missing_sensor_skipped(hass: HomeAssistant) -> None:
    """Test that configuration with missing sensor is skipped."""
    config = {
        DOMAIN: [
            {
                CONF_SOURCE_SENSOR: "sensor.nonexistent_sensor",
                CONF_ROOM_VOLUME: 50.0,
            }
        ]
    }

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    # No entry should be created for missing sensor
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 0
