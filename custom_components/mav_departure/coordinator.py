"""DataUpdateCoordinator for MÁV departure data."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Departure, MavApiClient, MavApiError
from .const import DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MavDepartureCoordinator(DataUpdateCoordinator[list[Departure]]):
    """Fetch MÁV departure data on a fixed schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MavApiClient,
        start_station_code: str,
        end_station_code: str,
        scan_interval_minutes: int = DEFAULT_SCAN_INTERVAL_MINUTES,
    ) -> None:
        self.start_station_code = start_station_code
        self.end_station_code = end_station_code
        self._client = client

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{start_station_code}_{end_station_code}",
            update_interval=timedelta(minutes=scan_interval_minutes),
        )

    async def _async_update_data(self) -> list[Departure]:
        """Fetch fresh departure data from the MÁV API."""
        try:
            return await self._client.get_departures(
                self.start_station_code,
                self.end_station_code,
            )
        except MavApiError as err:
            raise UpdateFailed(f"Error communicating with MÁV API: {err}") from err
