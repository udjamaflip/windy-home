"""Constants for the Windy Home integration."""

from __future__ import annotations

DOMAIN = "windy_home"
PLATFORMS = ["weather", "sensor", "camera"]

# Windy API endpoints
WINDY_POINT_FORECAST_URL = "https://api.windy.com/api/point-forecast/v2"
WINDY_WEBCAM_API_URL = "https://api.windy.com/webcams/api/v3/webcams"

# Config keys
CONF_LOCATION_NAME = "location_name"
CONF_FORECAST_MODEL = "forecast_model"
CONF_WEBCAM_API_KEY = "webcam_api_key"
CONF_WEBCAM_IDS = "webcam_ids"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ENABLE_WAVES = "enable_waves"

# Defaults
DEFAULT_FORECAST_MODEL = "gfs"
DEFAULT_UPDATE_INTERVAL = 10  # minutes
DEFAULT_WEBCAM_UPDATE_INTERVAL = 720  # minutes (12 hours)

# Available forecast models
FORECAST_MODELS = {
    "gfs": "GFS (Global)",
    "iconEu": "ICON-EU (Europe)",
    "arome": "AROME (France)",
    "namConus": "NAM CONUS (USA/Canada/Mexico)",
    "namHawaii": "NAM Hawaii",
    "namAlaska": "NAM Alaska",
    "gfsWave": "GFS Wave (Global)",
}

# Windy API point forecast parameters we request
FORECAST_PARAMS = [
    "temp",
    "dewpoint",
    "rh",
    "pressure",
    "wind",
    "windGust",
    "precip",
    "convPrecip",
    "cape",
    "lclouds",
    "mclouds",
    "hclouds",
    "ptype",
]

# Wave parameters (require gfsWave model)
WAVE_PARAMS = [
    "waves",
    "windWaves",
    "swell1",
    "swell2",
]

# Models that support wave data
WAVE_MODELS = {"gfsWave"}

# Windy precipitation type values
PTYPE_RAIN = 1
PTYPE_SNOW = 2
PTYPE_MIX = 3  # freezing rain / sleet

# Kelvin to Celsius offset
KELVIN_OFFSET = 273.15

# Attribution
ATTRIBUTION = "Data provided by Windy.com"

# Wave data keys returned by Windy (surface level)
# waves: combined wave height/period/direction
# windWaves: wind-wave component
# swell1/swell2: primary/secondary swell components
# Each returns: height (m), period (s), direction (°)
WAVE_KEY_HEIGHT_SUFFIX = "Height-surface"
WAVE_KEY_PERIOD_SUFFIX = "Period-surface"
WAVE_KEY_DIRECTION_SUFFIX = "Direction-surface"
