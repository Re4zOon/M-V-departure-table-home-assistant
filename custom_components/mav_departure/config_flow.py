"""Config flow for the MÁV Departure Table integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MavApiClient, MavApiError
from .const import (
    CONF_END_STATION_CODE,
    CONF_MAX_DEPARTURES,
    CONF_START_STATION_CODE,
    DEFAULT_MAX_DEPARTURES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
_NO_OFFERS_ERROR_TEXTS = {"no offers found", "máv api error: no offers found"}

_STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_START_STATION_CODE): str,
        vol.Required(CONF_END_STATION_CODE): str,
        vol.Optional(CONF_MAX_DEPARTURES, default=DEFAULT_MAX_DEPARTURES): vol.All(
            int, vol.Range(min=1, max=50)
        ),
    }
)


async def _validate_station_codes(
    hass: HomeAssistant,
    start_code: str,
    end_code: str,
) -> str | None:
    """Try a live API call and return an error key on failure, None on success."""
    session = async_get_clientsession(hass)
    client = MavApiClient(session)
    try:
        await client.get_departures(start_code, end_code)
    except MavApiError as err:
        error_text = str(err).strip().lower()
        if error_text in _NO_OFFERS_ERROR_TEXTS:
            return None
        _LOGGER.debug("Station code validation failed: %s", err)
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        return "unknown"
    return None


class MavDepartureConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MÁV Departure Table."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            start_code = user_input[CONF_START_STATION_CODE].strip()
            end_code = user_input[CONF_END_STATION_CODE].strip()

            # Prevent duplicate entries for the same route
            await self.async_set_unique_id(f"{start_code}_{end_code}")
            self._abort_if_unique_id_configured()

            error_key = await _validate_station_codes(self.hass, start_code, end_code)
            if error_key:
                errors["base"] = error_key
            else:
                title = f"MÁV {start_code} → {end_code}"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_START_STATION_CODE: start_code,
                        CONF_END_STATION_CODE: end_code,
                        CONF_MAX_DEPARTURES: user_input.get(
                            CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_STEP_SCHEMA,
            errors=errors,
        )
