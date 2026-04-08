"""Sensor platform for Windy Home — extra weather + wave sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLE_WAVES, DOMAIN
from .entity import WindyHomeEntity


@dataclass(kw_only=True)
class WindySensorDescription(SensorEntityDescription):
    """Describe a Windy sensor."""

    data_path: str  # dot-separated path into coordinator data
    coordinator_key: str = "weather"  # "weather" or "waves"


# ── Weather sensors ──────────────────────────────────────────────────────────

WEATHER_SENSORS: tuple[WindySensorDescription, ...] = (
    WindySensorDescription(
        key="cape",
        translation_key="cape",
        name="CAPE",
        native_unit_of_measurement="J/kg",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-lightning",
        data_path="current.cape",
    ),
    WindySensorDescription(
        key="wind_gust",
        translation_key="wind_gust",
        name="Wind Gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        data_path="current.wind_gust",
    ),
    WindySensorDescription(
        key="cloud_cover_low",
        translation_key="cloud_cover_low",
        name="Cloud Cover (Low)",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cloud",
        data_path="current.cloud_cover_low",
    ),
    WindySensorDescription(
        key="cloud_cover_mid",
        translation_key="cloud_cover_mid",
        name="Cloud Cover (Mid)",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cloud",
        data_path="current.cloud_cover_mid",
    ),
    WindySensorDescription(
        key="cloud_cover_high",
        translation_key="cloud_cover_high",
        name="Cloud Cover (High)",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cloud-outline",
        data_path="current.cloud_cover_high",
    ),
    WindySensorDescription(
        key="precipitation_type",
        translation_key="precipitation_type",
        name="Precipitation Type",
        icon="mdi:weather-snowy-rainy",
        data_path="current.precipitation_type",
    ),
    WindySensorDescription(
        key="convective_precipitation",
        translation_key="convective_precipitation",
        name="Convective Precipitation",
        native_unit_of_measurement="mm",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        data_path="current.convective_precipitation",
    ),
)

# ── Wave sensors ─────────────────────────────────────────────────────────────

WAVE_SENSORS: tuple[WindySensorDescription, ...] = (
    # Combined waves
    WindySensorDescription(
        key="wave_height",
        translation_key="wave_height",
        name="Wave Height",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:waves",
        data_path="current_waves.wave_height",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="wave_period",
        translation_key="wave_period",
        name="Wave Period",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:waves",
        data_path="current_waves.wave_period",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="wave_direction",
        translation_key="wave_direction",
        name="Wave Direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        data_path="current_waves.wave_direction",
        coordinator_key="waves",
    ),
    # Wind waves
    WindySensorDescription(
        key="wind_wave_height",
        translation_key="wind_wave_height",
        name="Wind Wave Height",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:waves-arrow-up",
        data_path="current_waves.wind_wave_height",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="wind_wave_period",
        translation_key="wind_wave_period",
        name="Wind Wave Period",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:waves-arrow-up",
        data_path="current_waves.wind_wave_period",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="wind_wave_direction",
        translation_key="wind_wave_direction",
        name="Wind Wave Direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        data_path="current_waves.wind_wave_direction",
        coordinator_key="waves",
    ),
    # Primary swell
    WindySensorDescription(
        key="swell1_height",
        translation_key="swell1_height",
        name="Primary Swell Height",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wave",
        data_path="current_waves.swell1_height",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="swell1_period",
        translation_key="swell1_period",
        name="Primary Swell Period",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wave",
        data_path="current_waves.swell1_period",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="swell1_direction",
        translation_key="swell1_direction",
        name="Primary Swell Direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        data_path="current_waves.swell1_direction",
        coordinator_key="waves",
    ),
    # Secondary swell
    WindySensorDescription(
        key="swell2_height",
        translation_key="swell2_height",
        name="Secondary Swell Height",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wave",
        data_path="current_waves.swell2_height",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="swell2_period",
        translation_key="swell2_period",
        name="Secondary Swell Period",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wave",
        data_path="current_waves.swell2_period",
        coordinator_key="waves",
    ),
    WindySensorDescription(
        key="swell2_direction",
        translation_key="swell2_direction",
        name="Secondary Swell Direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass-outline",
        data_path="current_waves.swell2_direction",
        coordinator_key="waves",
    ),
)


def _resolve_data_path(data: dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated path like 'current.cape' into data[current][cape]."""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Windy sensor entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    weather_coordinator = data["weather_coordinator"]

    entities: list[WindySensor] = []

    # Always add weather sensors
    for desc in WEATHER_SENSORS:
        entities.append(WindySensor(weather_coordinator, config_entry, desc))

    # Add wave sensors if enabled
    enable_waves = config_entry.options.get(CONF_ENABLE_WAVES, config_entry.data.get(CONF_ENABLE_WAVES, False))
    if enable_waves:
        for desc in WAVE_SENSORS:
            entities.append(WindySensor(weather_coordinator, config_entry, desc))

    async_add_entities(entities)


class WindySensor(WindyHomeEntity, SensorEntity):
    """A Windy sensor entity."""

    entity_description: WindySensorDescription

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        description: WindySensorDescription,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self.entity_description = description
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return _resolve_data_path(self.coordinator.data, self.entity_description.data_path)
