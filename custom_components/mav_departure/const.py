"""Constants for the MÁV Departure Table integration."""

DOMAIN = "mav_departure"
PLATFORMS = ["sensor"]

# MÁV API — current production endpoint used by jegy.mav.hu
MAV_API_URL = (
    "https://jegy-a.mav.hu/IK_API_PROD/api/OfferRequestApi/GetOfferRequest"
)
MAV_API_TIMEOUT = 30  # seconds

# Required passenger descriptor accepted by the offer-request endpoint
MAV_DEFAULT_PASSENGER = {
    "passengerCount": 1,
    "passengerId": 0,
    "customerTypeKey": "HU_44_025-065",
    "customerDiscountsKeys": [],
}

# Configuration keys
CONF_START_STATION_CODE = "start_station_code"
CONF_END_STATION_CODE = "end_station_code"
CONF_MAX_DEPARTURES = "max_departures"

# Defaults
DEFAULT_MAX_DEPARTURES = 10
DEFAULT_SCAN_INTERVAL_MINUTES = 5

# Sensor extra-state attribute names
ATTR_DEPARTURES = "departures"
ATTR_SCHEDULED = "scheduled"
ATTR_EXPECTED = "expected"
ATTR_DELAY_MINUTES = "delay_minutes"
ATTR_HAS_DELAY = "has_delay"
ATTR_TRAIN_SIGN = "train_sign"
ATTR_TRAIN_TYPE = "train_type"
ATTR_TRAIN_ORIGIN = "train_origin"
ATTR_TRAIN_DESTINATION = "train_destination"
ATTR_TRAVEL_TIME_MINUTES = "travel_time_minutes"
ATTR_START_STATION_CODE = "start_station_code"
ATTR_END_STATION_CODE = "end_station_code"
ATTR_LAST_ERROR = "last_error"
