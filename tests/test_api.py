"""Tests for the MÁV API client — parsing logic only (no network calls)."""

from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Build minimal stubs for every homeassistant sub-module we need so that the
# integration modules can be imported without a running HA environment.
# ---------------------------------------------------------------------------

TZ_CET = timezone(timedelta(hours=1))


def _register(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# homeassistant (top-level package must be a real package-like object)
ha = _register("homeassistant")
ha.__path__ = []  # mark as package

# homeassistant.util
ha_util = _register("homeassistant.util")
ha_util.__path__ = []

# homeassistant.util.dt
ha_dt = _register("homeassistant.util.dt")


def _stub_parse_datetime(value: str):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


ha_dt.parse_datetime = _stub_parse_datetime
ha_dt.now = lambda: datetime.now(tz=TZ_CET)
ha_dt.as_local = lambda dt: dt.astimezone(TZ_CET)
ha_util.dt = ha_dt

# homeassistant.config_entries
ha_ce = _register("homeassistant.config_entries")


class _FakeConfigFlow:
    def __init_subclass__(cls, **kwargs):
        return super().__init_subclass__()


ha_ce.ConfigEntry = object
ha_ce.ConfigFlow = _FakeConfigFlow
ha_ce.FlowResult = dict

# homeassistant.core
ha_core = _register("homeassistant.core")
ha_core.HomeAssistant = object

# homeassistant.components
ha_components = _register("homeassistant.components")
ha_components.__path__ = []

# homeassistant.components.sensor
ha_sensor = _register("homeassistant.components.sensor")
ha_sensor.SensorEntity = object


class _FakeSensorDeviceClass:
    TIMESTAMP = "timestamp"


ha_sensor.SensorDeviceClass = _FakeSensorDeviceClass

# homeassistant.helpers
ha_helpers = _register("homeassistant.helpers")
ha_helpers.__path__ = []

# homeassistant.helpers.aiohttp_client
ha_aio = _register("homeassistant.helpers.aiohttp_client")
ha_aio.async_get_clientsession = MagicMock()

# homeassistant.helpers.entity_platform
ha_ep = _register("homeassistant.helpers.entity_platform")
ha_ep.AddEntitiesCallback = object

# homeassistant.helpers.update_coordinator
ha_uc = _register("homeassistant.helpers.update_coordinator")


class _FakeCoordinator:
    def __class_getitem__(cls, item):
        return cls


class _FakeCoordinatorEntity:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator


ha_uc.DataUpdateCoordinator = _FakeCoordinator
ha_uc.UpdateFailed = Exception
ha_uc.CoordinatorEntity = _FakeCoordinatorEntity

# voluptuous (used by config_flow)
vol_mod = _register("voluptuous")
vol_mod.Schema = MagicMock(return_value=MagicMock())
vol_mod.Required = MagicMock(side_effect=lambda k: k)
vol_mod.Optional = MagicMock(side_effect=lambda k, **kw: k)
vol_mod.All = MagicMock(side_effect=lambda *a: a[0])
vol_mod.Range = MagicMock()

# ---------------------------------------------------------------------------
# Now we can import our module under test
# ---------------------------------------------------------------------------

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.mav_departure.api import (  # noqa: E402
    Departure,
    MavApiClient,
    MavApiError,
    _extract_train_info,
    _parse_datetime,
)
from custom_components.mav_departure.const import (  # noqa: E402
    CONF_END_STATION_CODE,
    CONF_START_STATION_CODE,
)
from custom_components.mav_departure.config_flow import _validate_station_codes  # noqa: E402
from custom_components.mav_departure.sensor import MavDepartureSensor  # noqa: E402

# ---------------------------------------------------------------------------
# _parse_datetime
# ---------------------------------------------------------------------------


class TestParseDatetime:
    def test_parses_iso_with_offset(self):
        result = _parse_datetime("2024-03-11T07:30:00+01:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 11
        assert result.hour == 7
        assert result.minute == 30

    def test_parses_iso_without_offset(self):
        result = _parse_datetime("2024-03-11T08:00:00")
        assert result is not None
        assert result.hour == 8

    def test_returns_none_for_empty_string(self):
        assert _parse_datetime("") is None

    def test_returns_none_for_garbage(self):
        assert _parse_datetime("not-a-date") is None

    def test_returns_none_for_none_input(self):
        assert _parse_datetime(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _extract_train_info
# ---------------------------------------------------------------------------


class TestExtractTrainInfo:
    # NOTE: MÁV API uses a misspelled key "destionationStation".
    _DEST_KEY = "destionationStation"

    def _make_route(
        self,
        jel: str,
        kind: str,
        origin: str = "Budapest-Keleti",
        destination: str = "Győr",
    ) -> dict:
        return {
            "details": {
                "routes": [
                    {
                        "startStation": {"name": origin},
                        self._DEST_KEY: {"name": destination},
                        "trainDetails": {
                            "viszonylatiJel": {"jel": jel},
                            "trainKind": {"name": kind},
                        }
                    }
                ]
            }
        }

    def test_extracts_sign_and_type(self):
        route = self._make_route("IC 703", "InterCity")
        sign, kind, origin, destination = _extract_train_info(route)
        assert sign == "IC 703"
        assert kind == "InterCity"
        assert origin == "Budapest-Keleti"
        assert destination == "Győr"

    def test_returns_empty_strings_when_details_missing(self):
        sign, kind, origin, destination = _extract_train_info({})
        assert sign == ""
        assert kind == ""
        assert origin == ""
        assert destination == ""

    def test_returns_empty_strings_when_routes_empty(self):
        sign, kind, origin, destination = _extract_train_info({"details": {"routes": []}})
        assert sign == ""
        assert kind == ""
        assert origin == ""
        assert destination == ""

    def test_tolerates_none_values(self):
        route = {
            "details": {
                "routes": [
                    {
                        "trainDetails": {
                            "viszonylatiJel": None,
                            "trainKind": None,
                        }
                    }
                ]
            }
        }
        sign, kind, origin, destination = _extract_train_info(route)
        assert sign == ""
        assert kind == ""
        assert origin == ""
        assert destination == ""

    def test_falls_back_to_first_last_leg_stations_without_sign(self):
        route = {
            "details": {
                "routes": [
                    {
                        "startStation": {"name": "Budapest-Keleti"},
                        self._DEST_KEY: {"name": "Győr"},
                        "trainDetails": {"viszonylatiJel": None, "trainKind": None},
                    },
                    {
                        "startStation": {"name": "Győr"},
                        self._DEST_KEY: {"name": "Hegyeshalom"},
                        "trainDetails": {"viszonylatiJel": None, "trainKind": None},
                    },
                ]
            }
        }
        sign, kind, origin, destination = _extract_train_info(route)
        assert sign == ""
        assert kind == ""
        assert origin == "Budapest-Keleti"
        assert destination == "Hegyeshalom"


# ---------------------------------------------------------------------------
# MavApiClient._parse_route (via the internal method directly)
# ---------------------------------------------------------------------------


class TestParseRoute:
    # NOTE: MÁV API uses a misspelled key "destionationStation".
    _DEST_KEY = "destionationStation"

    def setup_method(self):
        self.client = MavApiClient(session=MagicMock())

    def _make_route(
        self,
        scheduled: str,
        expected: str | None = None,
        travel_time: int = 60,
        jel: str = "IC 703",
        kind: str = "InterCity",
        origin: str = "Budapest-Keleti",
        destination: str = "Győr",
    ) -> dict:
        return {
            "departure": {
                "time": scheduled,
                "timeExpected": expected,
            },
            "travelTimeMin": travel_time,
            "details": {
                "routes": [
                    {
                        "startStation": {"name": origin},
                        self._DEST_KEY: {"name": destination},
                        "trainDetails": {
                            "viszonylatiJel": {"jel": jel},
                            "trainKind": {"name": kind},
                        }
                    }
                ]
            },
        }

    def test_on_time_departure(self):
        route = self._make_route("2024-03-11T07:30:00+01:00")
        dep = self.client._parse_route(route)
        assert dep is not None
        assert dep.has_delay is False
        assert dep.delay_minutes == 0
        assert dep.train_sign == "IC 703"
        assert dep.train_type == "InterCity"
        assert dep.train_origin == "Budapest-Keleti"
        assert dep.train_destination == "Győr"
        assert dep.travel_time_minutes == 60

    def test_delayed_departure(self):
        route = self._make_route(
            "2024-03-11T07:30:00+01:00",
            expected="2024-03-11T07:42:00+01:00",
        )
        dep = self.client._parse_route(route)
        assert dep is not None
        assert dep.has_delay is True
        assert dep.delay_minutes == 12

    def test_zero_year_expected_treated_as_on_time(self):
        """timeExpected of '0001-01-01T...' means no delay data available."""
        route = self._make_route(
            "2024-03-11T07:30:00+01:00",
            expected="0001-01-01T00:00:00+01:00",
        )
        dep = self.client._parse_route(route)
        assert dep is not None
        assert dep.has_delay is False
        assert dep.delay_minutes == 0

    def test_returns_none_when_scheduled_missing(self):
        route = {"departure": {}, "travelTimeMin": 30}
        dep = self.client._parse_route(route)
        assert dep is None

    def test_returns_none_when_departure_key_missing(self):
        dep = self.client._parse_route({})
        assert dep is None

    def test_negative_delay_not_reported(self):
        """Early departures should never show a negative delay."""
        route = self._make_route(
            "2024-03-11T07:30:00+01:00",
            expected="2024-03-11T07:25:00+01:00",  # 5 min early
        )
        dep = self.client._parse_route(route)
        assert dep is not None
        # An early departure is not flagged as a delay
        assert dep.has_delay is False
        assert dep.delay_minutes == 0

    def test_parse_response_skips_bad_entries(self):
        data = {
            "route": [
                {},  # missing departure key → should be skipped
                self._make_route("2024-03-11T08:00:00+01:00"),
            ]
        }
        result = self.client._parse_response(data)
        assert len(result) == 1
        assert result[0].train_sign == "IC 703"

    def test_parse_response_raises_for_api_error_message(self):
        with pytest.raises(MavApiError, match="No offers found"):
            self.client._parse_response({"errorMessage": "No offers found"})

    def test_parse_response_raises_when_route_missing(self):
        with pytest.raises(MavApiError, match="missing route"):
            self.client._parse_response({})

    def test_parse_response_raises_when_route_shape_invalid(self):
        with pytest.raises(MavApiError, match="invalid route format"):
            self.client._parse_response({"route": {"not": "a list"}})


def test_get_departures_raises_mavapierror_on_invalid_json():
    class _InvalidJsonResponse:
        def raise_for_status(self):
            return None

        async def json(self, content_type=None):
            raise ValueError("invalid json")

        async def text(self):
            return "<html>bad gateway</html>"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _Session:
        def post(self, *args, **kwargs):
            return _InvalidJsonResponse()

    async def _run_invalid_json_scenario():
        client = MavApiClient(session=_Session())
        with pytest.raises(MavApiError, match="invalid JSON"):
            await client.get_departures("005501016", "005500709")

    asyncio.run(_run_invalid_json_scenario())


def test_validate_station_codes_allows_no_offers(monkeypatch):
    class _RaisingNoOffersClient:
        def __init__(self, _session):
            pass

        async def get_departures(self, _start, _end):
            raise MavApiError("MÁV API returned error: No offers found")

    monkeypatch.setattr(
        "custom_components.mav_departure.config_flow.async_get_clientsession",
        lambda _hass: object(),
    )
    monkeypatch.setattr(
        "custom_components.mav_departure.config_flow.MavApiClient",
        _RaisingNoOffersClient,
    )

    assert asyncio.run(_validate_station_codes(object(), "005501016", "005500709")) is None


def test_validate_station_codes_allows_plain_no_offers(monkeypatch):
    class _RaisingNoOffersClient:
        def __init__(self, _session):
            pass

        async def get_departures(self, _start, _end):
            raise MavApiError("No offers found")

    monkeypatch.setattr(
        "custom_components.mav_departure.config_flow.async_get_clientsession",
        lambda _hass: object(),
    )
    monkeypatch.setattr(
        "custom_components.mav_departure.config_flow.MavApiClient",
        _RaisingNoOffersClient,
    )

    assert asyncio.run(_validate_station_codes(object(), "005501016", "005500709")) is None


def test_validate_station_codes_still_returns_cannot_connect(monkeypatch):
    class _RaisingConnectionClient:
        def __init__(self, _session):
            pass

        async def get_departures(self, _start, _end):
            raise MavApiError("gateway timeout")

    monkeypatch.setattr(
        "custom_components.mav_departure.config_flow.async_get_clientsession",
        lambda _hass: object(),
    )
    monkeypatch.setattr(
        "custom_components.mav_departure.config_flow.MavApiClient",
        _RaisingConnectionClient,
    )

    assert (
        asyncio.run(_validate_station_codes(object(), "005501016", "005500709"))
        == "cannot_connect"
    )


def test_sensor_native_value_is_datetime_timestamp():
    dep = Departure(
        scheduled_departure=datetime(2024, 3, 11, 7, 30, tzinfo=timezone.utc),
        expected_departure=datetime(2024, 3, 11, 7, 30, tzinfo=timezone.utc),
        delay_minutes=0,
        has_delay=False,
        train_sign="IC 703",
        train_type="InterCity",
        train_origin="Budapest-Keleti",
        train_destination="Győr",
        travel_time_minutes=60,
    )
    coordinator = types.SimpleNamespace(data=[dep])
    entry = types.SimpleNamespace(
        data={
            CONF_START_STATION_CODE: "005501016",
            CONF_END_STATION_CODE: "005500709",
        }
    )

    sensor = MavDepartureSensor(coordinator, entry)
    assert sensor.native_value is not None
    assert isinstance(sensor.native_value, datetime)
    assert sensor._attr_device_class == "timestamp"
