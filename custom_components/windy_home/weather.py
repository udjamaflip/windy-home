"""Weather platform for Windy Home."""

from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WindyHomeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Windy weather platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["weather_coordinator"]
    async_add_entities([WindyWeatherEntity(coordinator, config_entry)])


class WindyWeatherEntity(WindyHomeEntity, WeatherEntity):
    """Windy weather entity providing current conditions and hourly forecast."""

    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_translation_key = "windy_weather"

    def __init__(self, coordinator, config_entry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_weather"
        self._attr_name = "Weather"

    @property
    def supported_features(self) -> WeatherEntityFeature:
        return WeatherEntityFeature.FORECAST_HOURLY

    @property
    def _current(self) -> dict[str, Any]:
        if self.coordinator.data:
            return self.coordinator.data.get("current", {})
        return {}

    @property
    def condition(self) -> str | None:
        return self._current.get("condition")

    @property
    def native_temperature(self) -> float | None:
        return self._current.get("temperature")

    @property
    def humidity(self) -> float | None:
        return self._current.get("humidity")

    @property
    def native_pressure(self) -> float | None:
        return self._current.get("pressure")

    @property
    def native_wind_speed(self) -> float | None:
        return self._current.get("wind_speed")

    @property
    def wind_bearing(self) -> float | None:
        return self._current.get("wind_bearing")

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self._current.get("wind_gust")

    @property
    def native_dew_point(self) -> float | None:
        return self._current.get("dew_point")

    @property
    def cloud_coverage(self) -> int | None:
        val = self._current.get("cloud_cover")
        return int(val) if val is not None else None

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return hourly forecast."""
        if not self.coordinator.data:
            return None

        hourly = self.coordinator.data.get("hourly", [])
        forecasts: list[Forecast] = []
        for entry in hourly:
            forecasts.append(
                Forecast(
                    datetime=entry["datetime"],
                    condition=entry.get("condition"),
                    native_temperature=entry.get("temperature"),
                    humidity=entry.get("humidity"),
                    native_wind_speed=entry.get("wind_speed"),
                    wind_bearing=entry.get("wind_bearing"),
                    native_wind_gust_speed=entry.get("wind_gust"),
                    native_pressure=entry.get("pressure"),
                    native_precipitation=entry.get("precipitation"),
                    native_dew_point=entry.get("dew_point"),
                )
            )
        return forecasts
