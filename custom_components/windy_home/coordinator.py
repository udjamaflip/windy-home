"""Data update coordinators for Windy Home."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    WindyAuthError,
    WindyConnectionError,
    WindyPointForecastClient,
    WindyWebcamClient,
)
from .const import (
    DOMAIN,
    KELVIN_OFFSET,
    PTYPE_MIX,
    PTYPE_SNOW,
)

_LOGGER = logging.getLogger(__name__)


def _wind_from_uv(u: float, v: float) -> tuple[float, float]:
    """Convert u/v wind components (m/s) to speed (m/s) and bearing (degrees).

    u = east-west component (positive = from west)
    v = north-south component (positive = from south)
    Meteorological bearing = direction wind is coming FROM.
    """
    speed = math.sqrt(u * u + v * v)
    # atan2 gives angle of the vector the wind is blowing TO;
    # add 180° to get the direction it's coming FROM.
    bearing_rad = math.atan2(u, v)
    bearing_deg = (math.degrees(bearing_rad) + 180) % 360
    return speed, bearing_deg


def _kelvin_to_celsius(k: float) -> float:
    """Convert Kelvin to Celsius."""
    return k - KELVIN_OFFSET


def _map_condition(
    cloud_pct: float,
    precip_mm: float,
    ptype: int | None,
    is_day: bool = True,
) -> str:
    """Map Windy parameters to HA weather condition strings."""
    if precip_mm > 5.0:
        if ptype == PTYPE_SNOW:
            return "snowy"
        if ptype == PTYPE_MIX:
            return "snowy-rainy"
        return "pouring"

    if precip_mm > 0.2:
        if ptype == PTYPE_SNOW:
            return "snowy"
        if ptype == PTYPE_MIX:
            return "snowy-rainy"
        return "rainy"

    if cloud_pct > 80:
        return "cloudy"
    if cloud_pct > 30:
        return "partlycloudy"

    return "sunny" if is_day else "clear-night"


class WindyWeatherCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Windy Point Forecast data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: WindyPointForecastClient,
        lat: float,
        lon: float,
        model: str,
        enable_waves: bool,
        update_interval_min: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_weather",
            config_entry=config_entry,
            update_interval=timedelta(minutes=update_interval_min),
        )
        self._client = client
        self._lat = lat
        self._lon = lon
        self._model = model
        self._enable_waves = enable_waves

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and parse forecast data."""
        try:
            raw = await self._client.fetch(
                self._lat,
                self._lon,
                model=self._model,
                include_waves=self._enable_waves,
            )
        except WindyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except WindyConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

        return self._parse(raw)

    def _parse(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse raw Windy response into structured data."""
        weather = raw.get("weather", {})
        if not weather:
            raise UpdateFailed("Empty weather response")

        timestamps = weather.get("ts", [])
        if not timestamps:
            raise UpdateFailed("No timestamps in response")

        # Build hourly forecast entries
        hourly: list[dict[str, Any]] = []
        now_ms = datetime.now(timezone.utc).timestamp() * 1000

        for i, ts_ms in enumerate(timestamps):
            entry = self._parse_entry(weather, i, ts_ms)
            hourly.append(entry)

        # Find current conditions: nearest timestamp to now
        current_idx = 0
        min_diff = abs(timestamps[0] - now_ms)
        for i, ts_ms in enumerate(timestamps):
            diff = abs(ts_ms - now_ms)
            if diff < min_diff:
                min_diff = diff
                current_idx = i

        current = hourly[current_idx] if hourly else {}

        # Wave data
        waves_hourly: list[dict[str, Any]] | None = None
        current_waves: dict[str, Any] | None = None
        wave_raw = raw.get("waves")
        if wave_raw:
            wave_ts = wave_raw.get("ts", [])
            waves_hourly = []
            for i, ts_ms in enumerate(wave_ts):
                w_entry = self._parse_wave_entry(wave_raw, i, ts_ms)
                waves_hourly.append(w_entry)

            if waves_hourly:
                # Find nearest wave timestamp to now
                wave_idx = 0
                min_diff_w = abs(wave_ts[0] - now_ms)
                for i, ts_ms in enumerate(wave_ts):
                    diff = abs(ts_ms - now_ms)
                    if diff < min_diff_w:
                        min_diff_w = diff
                        wave_idx = i
                current_waves = waves_hourly[wave_idx]

        return {
            "current": current,
            "hourly": hourly,
            "current_waves": current_waves,
            "waves_hourly": waves_hourly,
        }

    def _parse_entry(self, data: dict[str, Any], idx: int, ts_ms: int) -> dict[str, Any]:
        """Parse a single forecast time step."""

        def _get(key: str) -> float | None:
            arr = data.get(key)
            if arr and idx < len(arr):
                return arr[idx]
            return None

        temp_k = _get("temp-surface")
        dewpoint_k = _get("dewpoint-surface")
        rh = _get("rh-surface")
        pressure = _get("pressure-surface")
        wind_u = _get("wind_u-surface")
        wind_v = _get("wind_v-surface")
        gust = _get("gust-surface")
        precip = _get("past3hprecip-surface") or _get("precip-surface") or 0.0
        conv_precip = _get("past3hconvprecip-surface") or _get("convPrecip-surface") or 0.0
        cape = _get("cape-surface")
        lclouds = _get("lclouds-surface") or 0.0
        mclouds = _get("mclouds-surface") or 0.0
        hclouds = _get("hclouds-surface") or 0.0
        ptype = _get("ptype-surface")

        # Compute derived values
        temp_c = _kelvin_to_celsius(temp_k) if temp_k is not None else None
        dewpoint_c = _kelvin_to_celsius(dewpoint_k) if dewpoint_k is not None else None

        wind_speed = None
        wind_bearing = None
        if wind_u is not None and wind_v is not None:
            wind_speed, wind_bearing = _wind_from_uv(wind_u, wind_v)

        # Pressure from Pa to hPa
        pressure_hpa = pressure / 100.0 if pressure is not None else None

        # Cloud cover: max of low/mid/high (each 0-100%)
        cloud_pct = max(lclouds, mclouds, hclouds)

        dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

        # Approximate local solar time from longitude (15° per hour offset)
        solar_offset_hours = self._lon / 15.0
        local_solar_hour = (dt_utc.hour + solar_offset_hours) % 24
        is_day = 6.0 <= local_solar_hour <= 18.0

        condition = _map_condition(cloud_pct, precip, int(ptype) if ptype is not None else None, is_day)

        return {
            "datetime": dt_utc.isoformat(),
            "temperature": round(temp_c, 1) if temp_c is not None else None,
            "dew_point": round(dewpoint_c, 1) if dewpoint_c is not None else None,
            "humidity": round(rh, 1) if rh is not None else None,
            "pressure": round(pressure_hpa, 1) if pressure_hpa is not None else None,
            "wind_speed": round(wind_speed, 1) if wind_speed is not None else None,
            "wind_bearing": round(wind_bearing, 0) if wind_bearing is not None else None,
            "wind_gust": round(gust, 1) if gust is not None else None,
            "precipitation": round(precip, 2),
            "convective_precipitation": round(conv_precip, 2),
            "cape": round(cape, 0) if cape is not None else None,
            "cloud_cover_low": round(lclouds, 0),
            "cloud_cover_mid": round(mclouds, 0),
            "cloud_cover_high": round(hclouds, 0),
            "cloud_cover": round(cloud_pct, 0),
            "precipitation_type": int(ptype) if ptype is not None else None,
            "condition": condition,
        }

    def _parse_wave_entry(self, data: dict[str, Any], idx: int, ts_ms: int) -> dict[str, Any]:
        """Parse a single wave forecast time step."""

        def _get(key: str) -> float | None:
            arr = data.get(key)
            if arr and idx < len(arr):
                return arr[idx]
            return None

        dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

        return {
            "datetime": dt_utc.isoformat(),
            # Combined waves
            "wave_height": _get("waves_height-surface"),
            "wave_period": _get("waves_period-surface"),
            "wave_direction": _get("waves_direction-surface"),
            # Wind waves
            "wind_wave_height": _get("windWaves_height-surface"),
            "wind_wave_period": _get("windWaves_period-surface"),
            "wind_wave_direction": _get("windWaves_direction-surface"),
            # Primary swell
            "swell1_height": _get("swell1_height-surface"),
            "swell1_period": _get("swell1_period-surface"),
            "swell1_direction": _get("swell1_direction-surface"),
            # Secondary swell
            "swell2_height": _get("swell2_height-surface"),
            "swell2_period": _get("swell2_period-surface"),
            "swell2_direction": _get("swell2_direction-surface"),
        }


class WindyWebcamCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for Windy Webcam data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: WindyWebcamClient,
        webcam_ids: list[str],
        update_interval_min: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_webcams",
            config_entry=config_entry,
            update_interval=timedelta(minutes=update_interval_min),
        )
        self._client = client
        self._webcam_ids = webcam_ids

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch webcam data."""
        if not self._webcam_ids:
            return []
        try:
            return await self._client.get_webcams(self._webcam_ids)
        except WindyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Webcam error: {err}") from err
