"""Tests for Windy Home coordinator parsing logic."""

from __future__ import annotations

import math

import pytest

from custom_components.windy_home.const import PTYPE_MIX, PTYPE_RAIN, PTYPE_SNOW
from custom_components.windy_home.coordinator import (
    WindyWeatherCoordinator,
    _kelvin_to_celsius,
    _map_condition,
    _wind_from_uv,
)

from .conftest import MOCK_POINT_FORECAST_RESPONSE, MOCK_WAVE_RESPONSE

# ── Unit conversion tests ───────────────────────────────────────────────────


class TestKelvinToCelsius:
    def test_freezing_point(self):
        assert _kelvin_to_celsius(273.15) == pytest.approx(0.0)

    def test_boiling_point(self):
        assert _kelvin_to_celsius(373.15) == pytest.approx(100.0)

    def test_room_temp(self):
        assert _kelvin_to_celsius(293.15) == pytest.approx(20.0)

    def test_negative(self):
        assert _kelvin_to_celsius(263.15) == pytest.approx(-10.0)


class TestWindFromUV:
    def test_pure_south_wind(self):
        """Wind from south: u=0, v positive (blowing northward)."""
        speed, bearing = _wind_from_uv(0, 5)
        assert speed == pytest.approx(5.0)
        assert bearing == pytest.approx(180.0)

    def test_pure_north_wind(self):
        """Wind from north: u=0, v negative (blowing southward)."""
        speed, bearing = _wind_from_uv(0, -5)
        assert speed == pytest.approx(5.0)
        assert bearing == pytest.approx(0.0, abs=0.1)

    def test_pure_west_wind(self):
        """Wind from west: u positive, v=0."""
        speed, bearing = _wind_from_uv(5, 0)
        assert speed == pytest.approx(5.0)
        assert bearing == pytest.approx(270.0)

    def test_pure_east_wind(self):
        """Wind from east: u negative, v=0."""
        speed, bearing = _wind_from_uv(-5, 0)
        assert speed == pytest.approx(5.0)
        assert bearing == pytest.approx(90.0)

    def test_calm(self):
        speed, bearing = _wind_from_uv(0, 0)
        assert speed == pytest.approx(0.0)

    def test_diagonal(self):
        """SW wind: u=3, v=4."""
        speed, bearing = _wind_from_uv(3, 4)
        assert speed == pytest.approx(5.0)
        # Wind vector points NE, so "from" is SW → ~216.87°
        expected_bearing = (math.degrees(math.atan2(3, 4)) + 180) % 360
        assert bearing == pytest.approx(expected_bearing)


class TestMapCondition:
    def test_clear_day(self):
        assert _map_condition(10, 0, None, is_day=True) == "sunny"

    def test_clear_night(self):
        assert _map_condition(10, 0, None, is_day=False) == "clear-night"

    def test_partly_cloudy(self):
        assert _map_condition(50, 0, None) == "partlycloudy"

    def test_cloudy(self):
        assert _map_condition(90, 0, None) == "cloudy"

    def test_light_rain(self):
        assert _map_condition(50, 1.0, PTYPE_RAIN) == "rainy"

    def test_heavy_rain(self):
        assert _map_condition(90, 10.0, PTYPE_RAIN) == "pouring"

    def test_snow(self):
        assert _map_condition(80, 2.0, PTYPE_SNOW) == "snowy"

    def test_heavy_snow(self):
        assert _map_condition(90, 8.0, PTYPE_SNOW) == "snowy"

    def test_mix(self):
        assert _map_condition(80, 2.0, PTYPE_MIX) == "snowy-rainy"


class TestWeatherCoordinatorParsing:
    """Test the _parse method directly with mock data."""

    def _make_coordinator(self):
        """Create a coordinator without hass for parsing tests."""
        coord = object.__new__(WindyWeatherCoordinator)
        coord._enable_waves = True
        coord._lon = 0.0
        return coord

    def test_parse_weather_only(self):
        coord = self._make_coordinator()
        raw = {"weather": MOCK_POINT_FORECAST_RESPONSE, "waves": None}
        result = coord._parse(raw)

        assert "current" in result
        assert "hourly" in result
        assert len(result["hourly"]) == 3
        assert result["waves_hourly"] is None

        # Check first entry: temp = 293.15K = 20.0°C
        first = result["hourly"][0]
        assert first["temperature"] == pytest.approx(20.0)
        assert first["humidity"] == pytest.approx(52.0)
        assert first["pressure"] == pytest.approx(1013.25, abs=0.1)
        assert first["wind_speed"] == pytest.approx(5.0)  # sqrt(3²+4²)
        assert first["wind_gust"] == pytest.approx(8.0)
        assert first["cape"] == pytest.approx(200.0)

    def test_parse_with_waves(self):
        coord = self._make_coordinator()
        raw = {
            "weather": MOCK_POINT_FORECAST_RESPONSE,
            "waves": MOCK_WAVE_RESPONSE,
        }
        result = coord._parse(raw)

        assert result["waves_hourly"] is not None
        assert len(result["waves_hourly"]) == 3
        assert result["current_waves"] is not None

        first_wave = result["waves_hourly"][0]
        assert first_wave["wave_height"] == pytest.approx(1.5)
        assert first_wave["wave_period"] == pytest.approx(8.0)
        assert first_wave["wave_direction"] == pytest.approx(180.0)
        assert first_wave["swell1_height"] == pytest.approx(1.2)
        assert first_wave["swell2_height"] == pytest.approx(0.3)

    def test_parse_empty_response_raises(self):
        coord = self._make_coordinator()
        with pytest.raises(Exception, match="Empty weather response"):
            coord._parse({"weather": {}, "waves": None})

    def test_parse_no_timestamps_raises(self):
        coord = self._make_coordinator()
        with pytest.raises(Exception, match="No timestamps"):
            coord._parse({"weather": {"ts": []}, "waves": None})
