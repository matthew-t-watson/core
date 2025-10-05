"""Config flow for the ache integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    CONF_MIN_R_SQUARED,
    CONF_ROOM_VOLUME,
    CONF_SOURCE_SENSOR,
    DEFAULT_MIN_R_SQUARED,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOURCE_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor"),
        ),
        vol.Required(CONF_ROOM_VOLUME): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=1000,
                step=0.1,
                unit_of_measurement="m³",
                mode=selector.NumberSelectorMode.BOX,
            ),
        ),
        vol.Optional(
            CONF_MIN_R_SQUARED, default=DEFAULT_MIN_R_SQUARED
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.5,
                max=1.0,
                step=0.01,
                mode=selector.NumberSelectorMode.SLIDER,
            ),
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    source_entity = data[CONF_SOURCE_SENSOR]

    # Validate that the source sensor exists
    if not hass.states.get(source_entity):
        raise CannotConnect

    # Return info that you want to store in the config entry
    return {"title": f"ACH ({source_entity})"}


class AcheConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ache."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle import from YAML configuration."""
        # Check if already configured with this source sensor
        await self.async_set_unique_id(import_data[CONF_SOURCE_SENSOR])
        self._abort_if_unique_id_configured()

        # Validate the imported data
        try:
            info = await validate_input(self.hass, import_data)
        except CannotConnect:
            _LOGGER.error(
                "Cannot import ache configuration: source sensor %s not found",
                import_data[CONF_SOURCE_SENSOR],
            )
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception("Error importing ache configuration")
            return self.async_abort(reason="unknown")

        # Create config entry from YAML import
        return self.async_create_entry(title=info["title"], data=import_data)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
