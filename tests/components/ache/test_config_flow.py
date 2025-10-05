"""Test the ache config flow."""

from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.components.ache.const import CONF_SOURCE_SENSOR, DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    # Create a test sensor
    hass.states.async_set("sensor.test_temperature", "25.5")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_SENSOR: "sensor.test_temperature",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ACH (sensor.test_temperature)"
    assert result["data"] == {
        CONF_SOURCE_SENSOR: "sensor.test_temperature",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_sensor_not_found(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle sensor not found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_SENSOR: "sensor.nonexistent",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    # Make sure the config flow tests finish with either an
    # FlowResultType.CREATE_ENTRY or FlowResultType.ABORT so
    # we can show the config flow is able to recover from an error.
    hass.states.async_set("sensor.test_temperature", "25.5")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_SENSOR: "sensor.test_temperature",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ACH (sensor.test_temperature)"
    assert result["data"] == {
        CONF_SOURCE_SENSOR: "sensor.test_temperature",
    }
    assert len(mock_setup_entry.mock_calls) == 1
