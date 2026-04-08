"""Config flow for Windy Home integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WindyAuthError, WindyConnectionError, WindyPointForecastClient
from .const import (
    CONF_ENABLE_WAVES,
    CONF_FORECAST_MODEL,
    CONF_LOCATION_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_WEBCAM_API_KEY,
    CONF_WEBCAM_IDS,
    DEFAULT_FORECAST_MODEL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    FORECAST_MODELS,
)

_LOGGER = logging.getLogger(__name__)


class WindyHomeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Windy Home."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step — API key, location, model."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate API key
            session = async_get_clientsession(self.hass)
            client = WindyPointForecastClient(session, user_input[CONF_API_KEY])
            try:
                await client.validate_key(
                    lat=user_input[CONF_LATITUDE],
                    lon=user_input[CONF_LONGITUDE],
                )
            except WindyAuthError:
                errors["base"] = "invalid_auth"
            except WindyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during validation")
                errors["base"] = "unknown"

            if not errors:
                # Check for duplicate location
                unique_id = f"{round(user_input[CONF_LATITUDE], 2)}_{round(user_input[CONF_LONGITUDE], 2)}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                self._data = user_input
                return self.async_create_entry(
                    title=user_input.get(
                        CONF_LOCATION_NAME,
                        f"Windy ({user_input[CONF_LATITUDE]}, {user_input[CONF_LONGITUDE]})",
                    ),
                    data=self._data,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_LOCATION_NAME, default="Home"): str,
                vol.Required(
                    CONF_LATITUDE,
                    default=self.hass.config.latitude,
                ): vol.Coerce(float),
                vol.Required(
                    CONF_LONGITUDE,
                    default=self.hass.config.longitude,
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_FORECAST_MODEL,
                    default=DEFAULT_FORECAST_MODEL,
                ): vol.In(FORECAST_MODELS),
                vol.Optional(CONF_ENABLE_WAVES, default=False): bool,
                vol.Optional(CONF_WEBCAM_API_KEY): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return WindyHomeOptionsFlow()


class WindyHomeOptionsFlow(OptionsFlow):
    """Handle options for Windy Home."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                vol.Optional(
                    CONF_FORECAST_MODEL,
                    default=current.get(
                        CONF_FORECAST_MODEL,
                        self.config_entry.data.get(CONF_FORECAST_MODEL, DEFAULT_FORECAST_MODEL),
                    ),
                ): vol.In(FORECAST_MODELS),
                vol.Optional(
                    CONF_ENABLE_WAVES,
                    default=current.get(
                        CONF_ENABLE_WAVES,
                        self.config_entry.data.get(CONF_ENABLE_WAVES, False),
                    ),
                ): bool,
                vol.Optional(
                    CONF_WEBCAM_API_KEY,
                    default=current.get(
                        CONF_WEBCAM_API_KEY,
                        self.config_entry.data.get(CONF_WEBCAM_API_KEY, ""),
                    ),
                ): str,
                vol.Optional(
                    CONF_WEBCAM_IDS,
                    default=current.get(
                        CONF_WEBCAM_IDS,
                        self.config_entry.data.get(CONF_WEBCAM_IDS, ""),
                    ),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
