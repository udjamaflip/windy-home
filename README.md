# Windy Home for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration for [Windy.com](https://www.windy.com) that provides weather forecasts, wave/swell data, and webcam feeds via the Windy API.

## Features

- **Weather Entity** — Current conditions + hourly forecast (temperature, humidity, wind, pressure, dew point, precipitation)
- **Wave Sensors** — Combined wave height/period/direction, wind waves, primary & secondary swell (via GFS Wave model)
- **Extra Sensors** — CAPE (storm energy), wind gust, cloud cover (low/mid/high), precipitation type, convective precipitation
- **Webcam Cameras** — Windy webcam feeds as Home Assistant camera entities

## Requirements

- A Windy API key — get one at [api.windy.com/keys](https://api.windy.com/keys)
- Home Assistant 2024.12.0 or newer

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant
2. Click the 3-dot menu → **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Search for "Windy Home" and install
5. Restart Home Assistant

### Manual

1. Download this repository
2. Copy the `custom_components/windy_home` folder into your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Windy Home**
3. Enter your Windy API key, location name, and coordinates (pre-filled from your HA home location)
4. Optionally select a forecast model and enable wave data
5. Done! Entities will appear under the new device

### Options

After setup, click **Configure** on the integration to adjust:

| Option | Default | Description |
|--------|---------|-------------|
| Update interval | 10 min | How often to poll Windy (5–60 minutes) |
| Forecast model | GFS | Weather model (GFS, ICON-EU, AROME, NAM variants) |
| Enable waves | Off | Fetch wave/swell data from GFS Wave model |
| Webcam IDs | — | Comma-separated Windy webcam IDs to add as cameras |

### Forecast Models

| Model | Coverage | Notes |
|-------|----------|-------|
| GFS | Global | Default, ~10 day horizon |
| ICON-EU | Europe | Higher resolution for EU |
| AROME | France & surroundings | Very high resolution |
| NAM CONUS | USA/Canada/Mexico | Regional detail |
| NAM Hawaii | Hawaii | |
| NAM Alaska | Alaska | |
| GFS Wave | Global oceans | Wave/swell data only |

## Entities

### Weather Entity
`weather.windy_home_weather` — Full weather entity with current conditions and hourly forecast. Works with the built-in Weather card.

### Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| CAPE | J/kg | Convective Available Potential Energy (storm risk) |
| Wind Gust | m/s | Current wind gust speed |
| Cloud Cover (Low/Mid/High) | % | Cloud cover at different altitudes |
| Precipitation Type | — | Rain (1), Snow (2), Mix (3) |
| Convective Precipitation | mm | Convective (thunderstorm) precipitation |

### Wave Sensors (when enabled)

| Sensor | Unit | Description |
|--------|------|-------------|
| Wave Height / Period / Direction | m / s / ° | Combined wave data |
| Wind Wave Height / Period / Direction | m / s / ° | Wind-generated wave component |
| Primary Swell Height / Period / Direction | m / s / ° | Primary ocean swell |
| Secondary Swell Height / Period / Direction | m / s / ° | Secondary swell component |

### Webcam Cameras
One camera entity per configured webcam ID, showing the latest preview image.

## Automation Examples

### High wind alert
```yaml
automation:
  - alias: "High Wind Warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.windy_home_wind_gust
        above: 20
    action:
      - service: notify.mobile_app
        data:
          title: "Wind Alert"
          message: "Wind gusts exceeding 20 m/s!"
```

### Storm risk (CAPE)
```yaml
automation:
  - alias: "Thunderstorm Risk"
    trigger:
      - platform: numeric_state
        entity_id: sensor.windy_home_cape
        above: 1000
    action:
      - service: notify.mobile_app
        data:
          title: "Storm Alert"
          message: "High CAPE value — thunderstorms possible!"
```

### Big wave alert
```yaml
automation:
  - alias: "Big Waves"
    trigger:
      - platform: numeric_state
        entity_id: sensor.windy_home_wave_height
        above: 3.0
    action:
      - service: notify.mobile_app
        data:
          title: "Surf Alert"
          message: "Wave height exceeding 3 meters!"
```

## License

MIT — see [LICENSE](LICENSE)
