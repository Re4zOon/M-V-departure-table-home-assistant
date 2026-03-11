"""The MÁV Departure Table integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MavApiClient
from .const import (
    CONF_END_STATION_CODE,
    CONF_START_STATION_CODE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MavDepartureCoordinator

CARD_JS = "mav-departure-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card as a static resource."""
    # Guard against duplicate registration across reloads.
    if CARD_URL not in hass.data.get("frontend_extra_module_url", set()):
        hass.http.register_static_path(
            CARD_URL,
            str(Path(__file__).parent / CARD_JS),
            True,
        )
        add_extra_js_url(hass, CARD_URL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MÁV Departure Table from a config entry."""
    session = async_get_clientsession(hass)
    client = MavApiClient(session)

    coordinator = MavDepartureCoordinator(
        hass=hass,
        client=client,
        start_station_code=entry.data[CONF_START_STATION_CODE],
        end_station_code=entry.data[CONF_END_STATION_CODE],
        scan_interval_minutes=DEFAULT_SCAN_INTERVAL_MINUTES,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
