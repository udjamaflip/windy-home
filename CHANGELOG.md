# Changelog

## [0.1.0] — 2026-04-07

### Added

- **Weather entity** — Current conditions (temperature, humidity, pressure, wind, cloud cover, dew point) from Windy Point Forecast API v2
- **Hourly forecast** — Up to 240 hours via `weather.get_forecasts` service
- **7 weather sensors** — CAPE, wind gust, cloud cover (low/mid/high), precipitation type, convective precipitation
- **12 wave sensors** — Wave height/period/direction, wind wave, primary swell, secondary swell (requires wave-capable model)
- **Webcam camera entities** — Live preview images from Windy Webcams API v3
- **Config flow** — UI-based setup with API key validation, location picker, model selection
- **Options flow** — Change update interval, forecast model, wave toggle, webcam API key, webcam IDs
- **5 custom Lovelace cards** — Weather overview, hourly forecast, wind compass, wave conditions, webcam viewer
- **Auto-registered dashboard cards** — Cards appear in the card picker automatically
- **Unit conversion** — Native HA unit system support (metric/imperial auto-conversion)
- **Multiple forecast models** — GFS, ECMWF, ICON-EU, and more
- **HACS compatible** — Install via HACS custom repository
