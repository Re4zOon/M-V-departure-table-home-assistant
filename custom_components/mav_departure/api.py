"""Async API client for the MÁV (Hungarian Railways) departure service.

Uses the production REST endpoint that powers jegy.mav.hu — no third-party
libraries are required beyond the aiohttp session provided by Home Assistant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

from homeassistant.util import dt as dt_util

from .const import MAV_API_TIMEOUT, MAV_API_URL, MAV_DEFAULT_PASSENGER

_LOGGER = logging.getLogger(__name__)

_MAV_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    # The API does not require authentication; an empty session token is fine.
    "UserSessionId": "''",
    "Language": "hu",
}


@dataclass
class Departure:
    """Represents a single train departure returned by the MÁV API."""

    scheduled_departure: datetime
    expected_departure: datetime
    delay_minutes: int
    has_delay: bool
    train_sign: str
    train_type: str
    train_origin: str
    train_destination: str
    travel_time_minutes: int


class MavApiError(Exception):
    """Raised when the MÁV API returns an unexpected error."""


class MavApiClient:
    """Thin async wrapper around the MÁV offer-request endpoint."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def get_departures(
        self,
        start_station_code: str,
        end_station_code: str,
        travel_date: datetime | None = None,
    ) -> list[Departure]:
        """Return upcoming departures between two stations.

        Args:
            start_station_code: 9-digit MÁV station code for the origin.
            end_station_code:   9-digit MÁV station code for the destination.
            travel_date:        Earliest departure time to include.  Defaults
                                to now (in the local HA timezone).

        Raises:
            MavApiError: On HTTP errors or unexpected response shapes.
        """
        if travel_date is None:
            travel_date = dt_util.now()

        payload: dict[str, Any] = {
            "offerkind": "1",
            "isOneWayTicket": True,
            "startStationCode": start_station_code,
            "endStationCode": end_station_code,
            "travelStartDate": travel_date.isoformat(),
            # NOTE: "passangers" is the MÁV API's own misspelling — must match exactly.
            "passangers": [MAV_DEFAULT_PASSENGER],
            "selectedServices": [],
            "selectedSearchServices": [],
            "isTravelEndTime": False,
            "innerStationsCodes": [],
            "isOfDetailedSearch": False,
        }

        timeout = aiohttp.ClientTimeout(total=MAV_API_TIMEOUT)
        try:
            async with self._session.post(
                MAV_API_URL,
                json=payload,
                headers=_MAV_HEADERS,
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                try:
                    data: dict[str, Any] = await response.json(content_type=None)
                except ValueError as err:
                    body = await response.text()
                    _LOGGER.debug("Unexpected non-JSON response from MÁV API: %s", body)
                    raise MavApiError("MÁV API returned invalid JSON") from err
        except aiohttp.ClientResponseError as err:
            raise MavApiError(
                f"MÁV API returned HTTP {err.status}: {err.message}"
            ) from err
        except aiohttp.ClientError as err:
            raise MavApiError(f"MÁV API request failed: {err}") from err

        return self._parse_response(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, data: dict[str, Any]) -> list[Departure]:
        error_message = data.get("errorMessage")
        if error_message:
            raise MavApiError(f"MÁV API returned error: {error_message}")

        routes = data.get("route")
        if routes is None:
            raise MavApiError("MÁV API response missing route data")
        if not isinstance(routes, list):
            raise MavApiError("MÁV API response has invalid route format")

        departures: list[Departure] = []
        for route in routes:
            if not isinstance(route, dict):
                _LOGGER.debug("Skipping non-dict route entry: %r", route)
                continue
            try:
                departure = self._parse_route(route)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Skipping unparseable route entry: %s", err)
                continue
            if departure is not None:
                departures.append(departure)
        return departures

    def _parse_route(self, route: dict[str, Any]) -> Departure | None:
        departure_info: dict[str, Any] = route.get("departure") or {}
        scheduled_str: str | None = departure_info.get("time")
        expected_str: str | None = departure_info.get("timeExpected")

        if not scheduled_str:
            return None

        scheduled = _parse_datetime(scheduled_str)
        if scheduled is None:
            return None

        # timeExpected can be absent, None, or "0001-01-01T…" (meaning on-time)
        expected: datetime | None = None
        if expected_str:
            candidate = _parse_datetime(expected_str)
            if candidate is not None and candidate.year > 1:
                expected = candidate

        effective = expected if expected is not None else scheduled
        has_delay = expected is not None and expected > scheduled
        delay_minutes = (
            max(0, int((expected - scheduled).total_seconds() / 60))
            if has_delay
            else 0
        )

        travel_time = int(route.get("travelTimeMin") or 0)
        train_sign, train_type, train_origin, train_destination = _extract_train_info(route)

        return Departure(
            scheduled_departure=scheduled,
            expected_departure=effective,
            delay_minutes=delay_minutes,
            has_delay=has_delay,
            train_sign=train_sign,
            train_type=train_type,
            train_origin=train_origin,
            train_destination=train_destination,
            travel_time_minutes=travel_time,
        )


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions — easy to unit-test)
# ---------------------------------------------------------------------------


def _parse_datetime(value: str) -> datetime | None:
    """Parse an ISO-8601 datetime string into a datetime object.

    Tries Home Assistant's dt_util.parse_datetime() first (which understands
    timezone offsets and HA's configured timezone), then falls back to
    datetime.fromisoformat(). The returned datetime may be naive or
    timezone-aware depending on the input string.
    """
    if not value:
        return None
    result = dt_util.parse_datetime(value)
    if result is not None:
        return result
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _extract_train_info(route: dict[str, Any]) -> tuple[str, str, str, str]:
    """Safely extract train sign/type and per-train origin/destination."""
    try:
        detail_routes: list = (route.get("details") or {}).get("routes") or []
        if not detail_routes:
            return ("", "", "", "")

        fallback_origin = ""
        fallback_destination = ""
        for detail_route in detail_routes:
            start_station = _extract_station_name(detail_route.get("startStation"))
            destination_obj = (
                detail_route.get("destionationStation")
                if "destionationStation" in detail_route
                else detail_route.get("destinationStation")
            )
            destination_station = _extract_station_name(
                destination_obj
            )
            if not fallback_origin and start_station:
                fallback_origin = start_station
            if destination_station:
                fallback_destination = destination_station

            train_details: dict = detail_route.get("trainDetails") or {}
            sign: str = (train_details.get("viszonylatiJel") or {}).get("jel", "")
            kind: str = (train_details.get("trainKind") or {}).get("name", "")
            if sign:
                return (
                    sign,
                    kind,
                    start_station or fallback_origin,
                    destination_station or fallback_destination,
                )

        return ("", "", fallback_origin, fallback_destination)
    except (AttributeError, IndexError, TypeError):
        return ("", "", "", "")


def _extract_station_name(station: Any) -> str:
    """Extract a station name from MÁV station object shape."""
    if isinstance(station, dict):
        return station.get("name") or ""
    return ""
