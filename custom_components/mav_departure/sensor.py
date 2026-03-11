"""MÁV Departure Table sensor platform."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DELAY_MINUTES,
    ATTR_DEPARTURES,
    ATTR_END_STATION_CODE,
    ATTR_EXPECTED,
    ATTR_HAS_DELAY,
    ATTR_SCHEDULED,
    ATTR_START_STATION_CODE,
    ATTR_TRAIN_SIGN,
    ATTR_TRAIN_TYPE,
    ATTR_TRAVEL_TIME_MINUTES,
    CONF_END_STATION_CODE,
    CONF_MAX_DEPARTURES,
    CONF_START_STATION_CODE,
    DEFAULT_MAX_DEPARTURES,
    DOMAIN,
)
from .coordinator import MavDepartureCoordinator

_LOGGER = logging.getLogger(__name__)

_ISO_FMT = "%Y-%m-%dT%H:%M:%S%z"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MÁV departure sensors from a config entry."""
    coordinator: MavDepartureCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MavDepartureSensor(coordinator, entry)], update_before_add=True)


class MavDepartureSensor(CoordinatorEntity[MavDepartureCoordinator], SensorEntity):
    """Sensor that exposes upcoming train departures for a single route."""

    _attr_icon = "mdi:train"
    _attr_has_entity_name = True
    _attr_name = None  # use the config-entry title as the entity name

    def __init__(
        self,
        coordinator: MavDepartureCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = (
            f"{entry.data[CONF_START_STATION_CODE]}"
            f"_{entry.data[CONF_END_STATION_CODE]}"
        )
        self._attr_extra_state_attributes: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # SensorEntity overrides
    # ------------------------------------------------------------------

    @property
    def native_value(self) -> str | None:
        """Return the next scheduled departure time as an ISO string, or None."""
        departures = self.coordinator.data
        if not departures:
            return None
        first = departures[0]
        dt: datetime = first.scheduled_departure
        if dt is None:
            return None
        # Return in the HA-local timezone so Lovelace formats it correctly
        local_dt = dt_util.as_local(dt) if dt.tzinfo else dt
        return local_dt.strftime(_ISO_FMT)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return all upcoming departures as a structured list."""
        departures = self.coordinator.data or []
        max_items: int = self._entry.data.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES)

        departure_list = []
        for dep in departures[:max_items]:
            scheduled = dep.scheduled_departure
            expected = dep.expected_departure

            departure_list.append(
                {
                    ATTR_SCHEDULED: (
                        dt_util.as_local(scheduled).strftime(_ISO_FMT)
                        if scheduled and scheduled.tzinfo
                        else str(scheduled)
                    ),
                    ATTR_EXPECTED: (
                        dt_util.as_local(expected).strftime(_ISO_FMT)
                        if expected and expected.tzinfo
                        else str(expected)
                    ),
                    ATTR_DELAY_MINUTES: dep.delay_minutes,
                    ATTR_HAS_DELAY: dep.has_delay,
                    ATTR_TRAIN_SIGN: dep.train_sign,
                    ATTR_TRAIN_TYPE: dep.train_type,
                    ATTR_TRAVEL_TIME_MINUTES: dep.travel_time_minutes,
                }
            )

        return {
            ATTR_DEPARTURES: departure_list,
            ATTR_START_STATION_CODE: self._entry.data[CONF_START_STATION_CODE],
            ATTR_END_STATION_CODE: self._entry.data[CONF_END_STATION_CODE],
        }
