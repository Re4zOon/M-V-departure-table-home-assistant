"""MÁV Departure Table sensor platform."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
    ATTR_TRAIN_DESTINATION,
    ATTR_TRAIN_ORIGIN,
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

def _serialize_datetime(value: datetime | None) -> str | None:
    """Serialize datetime values consistently as ISO-8601."""
    local_dt = _to_local_datetime(value)
    if local_dt is None:
        return None
    return local_dt.isoformat()


def _to_local_datetime(value: datetime | None) -> datetime | None:
    """Return a timezone-aware/localized datetime for Home Assistant."""
    if value is None:
        return None
    if value.tzinfo is None:
        default_tz = getattr(dt_util, "DEFAULT_TIME_ZONE", None)
        if default_tz is not None:
            value = value.replace(tzinfo=default_tz)
    return dt_util.as_local(value) if value.tzinfo else value


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
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: MavDepartureCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        start = entry.data[CONF_START_STATION_CODE]
        end = entry.data[CONF_END_STATION_CODE]
        self._attr_unique_id = f"{start}_{end}"
        self._attr_name = f"MÁV {start} \u2192 {end}"

    # ------------------------------------------------------------------
    # SensorEntity overrides
    # ------------------------------------------------------------------

    @property
    def native_value(self) -> datetime | None:
        """Return the next scheduled departure datetime, or None."""
        departures = self.coordinator.data
        if not departures:
            return None
        first = departures[0]
        return _to_local_datetime(first.scheduled_departure)

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
                    ATTR_SCHEDULED: _serialize_datetime(scheduled),
                    ATTR_EXPECTED: _serialize_datetime(expected),
                    ATTR_DELAY_MINUTES: dep.delay_minutes,
                    ATTR_HAS_DELAY: dep.has_delay,
                    ATTR_TRAIN_SIGN: dep.train_sign,
                    ATTR_TRAIN_TYPE: dep.train_type,
                    ATTR_TRAIN_ORIGIN: dep.train_origin,
                    ATTR_TRAIN_DESTINATION: dep.train_destination,
                    ATTR_TRAVEL_TIME_MINUTES: dep.travel_time_minutes,
                }
            )

        return {
            ATTR_DEPARTURES: departure_list,
            ATTR_START_STATION_CODE: self._entry.data[CONF_START_STATION_CODE],
            ATTR_END_STATION_CODE: self._entry.data[CONF_END_STATION_CODE],
        }
