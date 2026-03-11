"""Optional live E2E checks for MÁV API communication.

These tests are intentionally opt-in because they depend on external network
access and a third-party API being reachable.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

import aiohttp
import pytest

MAV_API_URL = "https://jegy-a.mav.hu/IK_API_PROD/api/OfferRequestApi/GetOfferRequest"


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E_MAV_API") != "1",
    reason="Set RUN_E2E_MAV_API=1 to run live MÁV API communication tests.",
)


def test_live_offer_request_returns_json() -> None:
    """Verify the live MÁV endpoint responds to a real offer request payload."""
    payload = {
        "offerkind": "1",
        "isOneWayTicket": True,
        "startStationCode": "005501016",  # Budapest-Keleti
        "endStationCode": "005500709",  # Győr
        # Use a buffered future timestamp to avoid edge cases around "now".
        "travelStartDate": (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat(),
        # NOTE: API field name is intentionally misspelled by MÁV.
        "passangers": [
            {
                "passengerCount": 1,
                "passengerId": 0,
                "customerTypeKey": "HU_44_025-065",
                "customerDiscountsKeys": [],
            }
        ],
        "selectedServices": [],
        "selectedSearchServices": [],
        "isTravelEndTime": False,
        "innerStationsCodes": [],
        "isOfDetailedSearch": False,
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        # "''" mirrors the value used by the production web client requests.
        "UserSessionId": "''",
        "Language": "hu",
    }

    async def _execute_live_request():
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(MAV_API_URL, json=payload, headers=headers) as response:
                assert response.status == 200
                return await response.json(content_type=None)

    data = asyncio.run(_execute_live_request())

    assert isinstance(data, dict)
    # We primarily care about API communication and schema-level compatibility.
    assert "route" in data or "errorMessage" in data
