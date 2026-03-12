"""The MÁV Departure Table integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
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

_LOGGER = logging.getLogger(__name__)

CARD_JS = "mav-departure-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"


async def _register_card(hass: HomeAssistant) -> None:
    """Register the Lovelace JS card as a frontend resource (idempotent)."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    internal = domain_data.setdefault("_internal", {})
    if internal.get("card_registered", False):
        return
    try:
        from homeassistant.components.frontend import add_extra_js_url
    except ImportError:
        _LOGGER.warning("Frontend component not available; skipping card registration")
        return
    if not hasattr(hass, "http") or hass.http is None:
        _LOGGER.warning("HTTP server not available; skipping card registration")
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / CARD_JS), True)]
    )
    add_extra_js_url(hass, CARD_URL)
    internal["card_registered"] = True


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card as a static resource (best-effort)."""
    await _register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MÁV Departure Table from a config entry."""
    await _register_card(hass)

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
