"""Tests for sensors — data path resolution and sensor descriptions."""

from __future__ import annotations

from custom_components.windy_home.sensor import (
    WAVE_SENSORS,
    WEATHER_SENSORS,
    _resolve_data_path,
)


class TestResolveDataPath:
    def test_simple_path(self):
        data = {"current": {"cape": 1500}}
        assert _resolve_data_path(data, "current.cape") == 1500

    def test_nested_path(self):
        data = {"current_waves": {"wave_height": 2.5}}
        assert _resolve_data_path(data, "current_waves.wave_height") == 2.5

    def test_missing_key(self):
        data = {"current": {"cape": 1500}}
        assert _resolve_data_path(data, "current.missing") is None

    def test_missing_top_level(self):
        data = {"current": {"cape": 1500}}
        assert _resolve_data_path(data, "nonexistent.cape") is None

    def test_none_data(self):
        assert _resolve_data_path({}, "current.cape") is None


class TestSensorDescriptions:
    def test_weather_sensors_have_unique_keys(self):
        keys = [s.key for s in WEATHER_SENSORS]
        assert len(keys) == len(set(keys))

    def test_wave_sensors_have_unique_keys(self):
        keys = [s.key for s in WAVE_SENSORS]
        assert len(keys) == len(set(keys))

    def test_wave_sensors_use_waves_coordinator(self):
        for s in WAVE_SENSORS:
            assert s.coordinator_key == "waves"

    def test_weather_sensors_use_weather_coordinator(self):
        for s in WEATHER_SENSORS:
            assert s.coordinator_key == "weather"

    def test_all_sensors_have_data_paths(self):
        for s in (*WEATHER_SENSORS, *WAVE_SENSORS):
            assert s.data_path, f"Sensor {s.key} missing data_path"
