# MÁV Departure Table for Home Assistant

A [HACS](https://hacs.xyz/) custom integration that pulls **real-time departure times and delays** from the MÁV (Magyar Államvasutak – Hungarian State Railways) API and exposes them as Home Assistant sensor entities.  A companion Lovelace card renders the data as a departure board directly on your dashboard.

---

## Features

- Real-time departure times from the official MÁV production API (`jegy.mav.hu`)
- Delay information highlighted in the dashboard card
- Multiple routes supported (add the integration multiple times)
- Configurable maximum number of departures per route
- Data refreshed every 5 minutes automatically
- Bilingual UI — English and Hungarian

---

## Screenshot

> _Once installed the card looks like a station departure board:_

| | |
|---|---|
| Train | From | To | Scheduled | Expected | Delay |
|-------|------|----|-----------|----------|-------|
| IC 924 | Budapest-Keleti | Győr | 07:30 | 07:30 | On time |
| RJX 64 | Budapest-Keleti | München Hbf | 07:45 | 07:52 | +7 min |
| IC 811 | Budapest-Keleti | Sopron | 08:00 | 08:00 | On time |

---

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations** → three-dot menu → **Custom repositories**.
2. Add `https://github.com/Re4zOon/M-V-departure-table-home-assistant` as an **Integration**.
3. Search for **MÁV Departure Table** and install it.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/mav_departure/` folder into your `<config>/custom_components/` directory.
2. Restart Home Assistant.

---

## Setup

### 1. Find your station codes

The MÁV API identifies stations by a 9-digit numeric code (e.g. `005501016` for Budapest-Keleti).

**How to find station codes:**

1. Open [https://jegy.mav.hu](https://jegy.mav.hu) in Chrome or Edge.
2. Press **F12** to open Developer Tools and go to the **Network** tab.
3. Enter your departure and destination stations and click **Search**.
4. Look for the `GetOfferRequest` POST request.
5. In the **Payload** tab you will see `startStationCode` and `endStationCode` — copy both values.

Some common codes:

| Station | Code |
|---------|------|
| Budapest-Keleti | `005501016` |
| Budapest-Nyugati | `005501024` |
| Budapest-Déli | `005501057` |
| Győr | `005500709` |
| Pécs | `005502186` |
| Debrecen | `005500476` |
| Miskolc-Tiszai | `005501497` |

### 2. Add the integration

1. Go to **Settings → Devices & Services → + Add Integration**.
2. Search for **MÁV Departure Table**.
3. Fill in:
   - **Origin station code** (e.g. `005501016`)
   - **Destination station code** (e.g. `005500709`)
   - **Maximum departures to display** (default: 10)
4. Click **Submit**.

The integration will immediately validate your station codes against the live API.

---

## Lovelace card

The Lovelace card is **automatically registered** when the integration is loaded — no manual resource setup is needed.

### Add the card to your dashboard

Edit your dashboard and add a manual card:

```yaml
type: custom:mav-departure-card
entity: sensor.mav_005501016_005500709
title: "Budapest-Keleti → Győr"
max_departures: 8
```

| Option | Required | Description |
|--------|----------|-------------|
| `entity` | ✅ | The sensor entity created by the integration |
| `title` | No | Card header text (defaults to the entity's friendly name) |
| `max_departures` | No | Override the maximum rows shown (default: 10) |

---

## Sensor attributes

Each sensor exposes the following attributes that you can use in automations or templates:

| Attribute | Type | Description |
|-----------|------|-------------|
| `departures` | list | List of departure objects (see below) |
| `start_station_code` | string | Origin station code |
| `end_station_code` | string | Destination station code |

Each item in `departures` contains:

| Field | Type | Description |
|-------|------|-------------|
| `scheduled` | ISO datetime | Planned departure time |
| `expected` | ISO datetime | Real-time expected departure time |
| `delay_minutes` | int | Delay in minutes (0 if on time) |
| `has_delay` | bool | `true` if the train is currently delayed |
| `train_sign` | string | Train identifier shown on boards (e.g. `IC 703`) |
| `train_type` | string | Service type (e.g. `InterCity`) |
| `train_origin` | string | Origin station for that train service |
| `train_destination` | string | Final destination station for that train service |
| `travel_time_minutes` | int | Total travel time in minutes |

### Example automation

```yaml
alias: "Notify me if my train is delayed"
trigger:
  - platform: template
    value_template: >
      {% set deps = state_attr('sensor.mav_005501016_005500709', 'departures') %}
      {% if deps and deps | length > 0 %}
        {{ deps[0].has_delay }}
      {% else %}
        false
      {% endif %}
action:
  - service: notify.mobile_app
    data:
      title: "Train delayed!"
      message: >
        {% set d = state_attr('sensor.mav_005501016_005500709', 'departures')[0] %}
        {{ d.train_sign }} is {{ d.delay_minutes }} minutes late.
        Expected at {{ d.expected[11:16] }}.
```

---

## API Notice

This integration uses the **public, unauthenticated** production API that powers `jegy.mav.hu`.  No API key is required.  The API is not officially documented; it was reverse-engineered by the community.  MÁV may change or restrict the endpoint at any time without notice.

---

## Contributing

Pull requests and issues are welcome.  Please open an issue before submitting large changes.

## License

MIT
