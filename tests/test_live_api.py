"""Live integration tests against the real Windy API.

Run with your API key:
    WINDY_API_KEY=your_key python -m pytest tests/test_live_api.py -v -s

These tests hit the actual Windy endpoints and validate the full pipeline:
API call → response parsing → coordinator data → entity-ready values.
"""

from __future__ import annotations

import os

import aiohttp
import pytest

from custom_components.windy_home.api import (
    WindyAuthError,
    WindyPointForecastClient,
    WindyWebcamClient,
)
from custom_components.windy_home.coordinator import (
    WindyWeatherCoordinator,
    _kelvin_to_celsius,
)

API_KEY = os.environ.get("WINDY_API_KEY", "")
SKIP_REASON = "Set WINDY_API_KEY env var to run live API tests"

# Santa Cruz, CA — coastal, good for wave testing
TEST_LAT = 36.97
TEST_LON = -122.03


pytestmark = pytest.mark.skipif(not API_KEY, reason=SKIP_REASON)


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


# ── Point Forecast API ──────────────────────────────────────────────────────


class TestLivePointForecast:
    """Test real Point Forecast API calls."""

    @pytest.mark.asyncio
    async def test_validate_key(self, session):
        """Real key validation against the API."""
        client = WindyPointForecastClient(session, API_KEY)
        result = await client.validate_key(lat=TEST_LAT, lon=TEST_LON)
        assert result is True
        print("✓ API key validated successfully")

    @pytest.mark.asyncio
    async def test_invalid_key_rejected(self, session):
        """Confirm a bogus key is rejected."""
        client = WindyPointForecastClient(session, "definitely-not-a-real-key")
        with pytest.raises(WindyAuthError):
            await client.validate_key()
        print("✓ Invalid key correctly rejected")

    @pytest.mark.asyncio
    async def test_fetch_weather(self, session):
        """Fetch weather data and validate the response structure."""
        client = WindyPointForecastClient(session, API_KEY)
        result = await client.fetch(TEST_LAT, TEST_LON, model="gfs", include_waves=False)

        weather = result["weather"]
        assert "ts" in weather, "Response missing 'ts' timestamps"
        assert len(weather["ts"]) > 0, "Empty timestamp array"

        # Check we got temperature data
        assert "temp-surface" in weather, "Missing temp-surface"
        assert len(weather["temp-surface"]) == len(weather["ts"])

        # Check wind components
        assert "wind_u-surface" in weather, "Missing wind_u-surface"
        assert "wind_v-surface" in weather, "Missing wind_v-surface"

        # Validate temperature is in Kelvin (should be ~250-320K for earth)
        first_temp = weather["temp-surface"][0]
        assert 200 < first_temp < 350, f"Temperature {first_temp}K seems wrong"

        temp_c = _kelvin_to_celsius(first_temp)
        print(f"✓ Weather data fetched: {len(weather['ts'])} timestamps")
        print(f"  First temp: {first_temp:.1f}K = {temp_c:.1f}°C")
        print(f"  Forecast horizon: {len(weather['ts'])} time steps")

    @pytest.mark.asyncio
    async def test_fetch_with_waves(self, session):
        """Fetch weather + wave data and validate both."""
        client = WindyPointForecastClient(session, API_KEY)
        result = await client.fetch(TEST_LAT, TEST_LON, model="gfs", include_waves=True)

        assert "weather" in result
        assert "waves" in result
        assert result["waves"] is not None, "Wave data should be present for coastal location"

        waves = result["waves"]
        assert "ts" in waves
        assert len(waves["ts"]) > 0

        # Check wave height exists
        assert "waves_height-surface" in waves, "Missing combined wave height"
        first_height = waves["waves_height-surface"][0]
        assert first_height >= 0, "Wave height can't be negative"

        print(f"✓ Wave data fetched: {len(waves['ts'])} timestamps")
        print(f"  Wave height: {first_height:.2f}m")

        if "swell1_height-surface" in waves:
            swell = waves["swell1_height-surface"][0]
            print(f"  Primary swell: {swell:.2f}m")

    @pytest.mark.asyncio
    async def test_full_parsing_pipeline(self, session):
        """Fetch real data and run it through the coordinator's parser."""
        client = WindyPointForecastClient(session, API_KEY)
        raw = await client.fetch(TEST_LAT, TEST_LON, model="gfs", include_waves=True)

        # Create a bare coordinator just for parsing
        coord = object.__new__(WindyWeatherCoordinator)
        coord._enable_waves = True
        parsed = coord._parse(raw)

        # Validate parsed structure
        assert "current" in parsed
        assert "hourly" in parsed
        assert len(parsed["hourly"]) > 0

        current = parsed["current"]
        print("\n✓ Full pipeline parsed successfully:")
        print("  Current conditions:")
        print(f"    Temperature: {current.get('temperature')}°C")
        print(f"    Humidity: {current.get('humidity')}%")
        print(f"    Pressure: {current.get('pressure')} hPa")
        print(f"    Wind speed: {current.get('wind_speed')} m/s")
        print(f"    Wind bearing: {current.get('wind_bearing')}°")
        print(f"    Wind gust: {current.get('wind_gust')} m/s")
        print(f"    CAPE: {current.get('cape')} J/kg")
        print(f"    Cloud cover: {current.get('cloud_cover')}%")
        print(f"    Condition: {current.get('condition')}")
        print(f"  Hourly forecast: {len(parsed['hourly'])} entries")

        # Validate all values are sane
        temp = current.get("temperature")
        assert temp is not None, "Temperature should not be None"
        assert -60 < temp < 60, f"Temperature {temp}°C seems unreasonable"

        pressure = current.get("pressure")
        assert pressure is not None
        assert 900 < pressure < 1100, f"Pressure {pressure}hPa seems unreasonable"

        wind = current.get("wind_speed")
        assert wind is not None
        assert 0 <= wind < 100, f"Wind {wind}m/s seems unreasonable"

        # Validate condition is a known HA value
        valid_conditions = {
            "clear-night",
            "cloudy",
            "exceptional",
            "fog",
            "hail",
            "lightning",
            "lightning-rainy",
            "partlycloudy",
            "pouring",
            "rainy",
            "snowy",
            "snowy-rainy",
            "sunny",
            "windy",
            "windy-variant",
        }
        assert current["condition"] in valid_conditions, f"Condition '{current['condition']}' not in HA condition list"

        # Check wave data
        if parsed.get("current_waves"):
            cw = parsed["current_waves"]
            print("  Wave data:")
            print(f"    Wave height: {cw.get('wave_height')}m")
            print(f"    Wave period: {cw.get('wave_period')}s")
            print(f"    Wave direction: {cw.get('wave_direction')}°")
            print(f"    Swell1 height: {cw.get('swell1_height')}m")
            print(f"    Swell2 height: {cw.get('swell2_height')}m")

        # Validate hourly forecast entries have required fields
        for entry in parsed["hourly"][:3]:
            assert "datetime" in entry
            assert "temperature" in entry
            assert "condition" in entry


# ── Webcam API ──────────────────────────────────────────────────────────────


class TestLiveWebcams:
    """Test real Webcam API calls."""

    @pytest.mark.asyncio
    async def test_search_nearby(self, session):
        """Search for webcams near the test location."""
        client = WindyWebcamClient(session, API_KEY)
        cams = await client.search_nearby(TEST_LAT, TEST_LON, radius_km=50)

        print(f"\n✓ Found {len(cams)} webcams within 50km of ({TEST_LAT}, {TEST_LON})")
        for cam in cams[:5]:
            title = cam.get("title", "Unknown")
            loc = cam.get("location", {})
            city = loc.get("city", "?")
            wid = cam.get("webcamId") or cam.get("id", "?")
            print(f"  [{wid}] {title} — {city}")

        # Should find at least some webcams near Santa Cruz
        assert len(cams) > 0, "Expected webcams near Santa Cruz, CA"

    @pytest.mark.asyncio
    async def test_webcam_has_image_url(self, session):
        """Verify webcam data includes usable image URLs."""
        client = WindyWebcamClient(session, API_KEY)
        cams = await client.search_nearby(TEST_LAT, TEST_LON, radius_km=50, limit=1)

        if not cams:
            pytest.skip("No webcams found nearby")

        cam = cams[0]
        images = cam.get("images", {})
        assert images, f"Webcam {cam.get('webcamId')} has no images"

        # Check for a usable preview URL
        found_url = False
        for key in ("current", "daylight"):
            img = images.get(key, {})
            url = img.get("preview") or img.get("thumbnail")
            if url:
                found_url = True
                print(f"✓ Webcam image URL found: {url[:80]}...")

                # Actually fetch the image to confirm it works
                async with session.get(url) as resp:
                    assert resp.status == 200, f"Image fetch failed: HTTP {resp.status}"
                    data = await resp.read()
                    assert len(data) > 100, "Image data too small"
                    print(f"  Image fetched: {len(data)} bytes")
                break

        assert found_url, "No preview/thumbnail URL found in webcam images"
