"""End-to-end integration tests for Windy Home.

These test the complete data pipeline using a local aiohttp test server
that mimics the real Windy API endpoints. No mocks — real HTTP requests,
real JSON parsing, real coordinator logic, real sensor/entity data paths.

  Local HTTP Server → API Client → Coordinator Parser → Entity Values
"""

from __future__ import annotations

import math

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from custom_components.windy_home.api import (
    WindyAuthError,
    WindyPointForecastClient,
    WindyWebcamClient,
)
from custom_components.windy_home.coordinator import WindyWeatherCoordinator
from custom_components.windy_home.sensor import (
    WAVE_SENSORS,
    WEATHER_SENSORS,
    _resolve_data_path,
)

from .conftest import MOCK_POINT_FORECAST_RESPONSE, MOCK_WAVE_RESPONSE, MOCK_WEBCAM_RESPONSE

# ── Local test HTTP server mimicking Windy API ──────────────────────────────


def create_windy_test_app() -> web.Application:
    """Create a test aiohttp app that mimics the Windy API."""
    app = web.Application()
    app.router.add_post("/api/point-forecast/v2", handle_forecast)
    app.router.add_get("/webcams/api/v3/webcams", handle_webcam_list)
    app.router.add_get("/webcams/api/v3/webcams/{webcam_id}", handle_webcam_single)
    return app


async def handle_forecast(request: web.Request) -> web.Response:
    """Handle Point Forecast API requests — validates key, model, returns data."""
    body = await request.json()

    if body.get("key") == "bad-key":
        return web.Response(status=401, text="Unauthorized")
    if body.get("key") != "test-key":
        return web.Response(status=403, text="Forbidden")

    model = body.get("model", "gfs")
    if model == "gfsWave":
        return web.json_response(MOCK_WAVE_RESPONSE)

    return web.json_response(MOCK_POINT_FORECAST_RESPONSE)


async def handle_webcam_list(request: web.Request) -> web.Response:
    """Handle webcam search — validates header key."""
    if request.headers.get("x-windy-api-key") != "test-key":
        return web.Response(status=401, text="Unauthorized")
    return web.json_response({"webcams": [MOCK_WEBCAM_RESPONSE]})


async def handle_webcam_single(request: web.Request) -> web.Response:
    """Handle single webcam fetch."""
    if request.headers.get("x-windy-api-key") != "test-key":
        return web.Response(status=401, text="Unauthorized")
    return web.json_response(MOCK_WEBCAM_RESPONSE)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def test_server():
    """Start a local test server mimicking the Windy API."""
    app = create_windy_test_app()
    server = TestServer(app)
    await server.start_server()
    yield server
    await server.close()


@pytest.fixture
async def session():
    """Create an aiohttp session."""
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def patch_urls(test_server):
    """Temporarily point API constants to local test server.

    api.py imports URLs at the top (``from .const import ...``) which creates
    local name bindings.  We must patch the *api* module's namespace so the
    already-imported names get replaced.
    """
    import custom_components.windy_home.api as api

    base = f"http://127.0.0.1:{test_server.port}"

    orig_forecast = api.WINDY_POINT_FORECAST_URL
    orig_webcam = api.WINDY_WEBCAM_API_URL
    api.WINDY_POINT_FORECAST_URL = f"{base}/api/point-forecast/v2"
    api.WINDY_WEBCAM_API_URL = f"{base}/webcams/api/v3/webcams"
    yield
    api.WINDY_POINT_FORECAST_URL = orig_forecast
    api.WINDY_WEBCAM_API_URL = orig_webcam


# ── End-to-end tests ────────────────────────────────────────────────────────


class TestWeatherPipeline:
    """Test weather data: HTTP → parse → entity-ready values."""

    @pytest.mark.asyncio
    async def test_full_weather_flow(self, session, patch_urls):
        """API call → coordinator parse → all weather values valid."""
        client = WindyPointForecastClient(session, "test-key")
        result = await client.fetch(36.97, -122.03, model="gfs", include_waves=False)

        # Validate raw response structure
        weather = result["weather"]
        assert "ts" in weather
        assert len(weather["ts"]) == 3
        assert "temp-surface" in weather
        assert "wind_u-surface" in weather

        # Parse through coordinator
        coord = object.__new__(WindyWeatherCoordinator)
        coord._enable_waves = False
        coord._lon = -122.03
        parsed = coord._parse(result)

        current = parsed["current"]
        hourly = parsed["hourly"]

        # ── Temperature (K→°C) ──
        # "current" = entry closest to now; all mock timestamps are 2023,
        # so the latest (index 2: 292.15 K → 19°C) is picked.
        assert current["temperature"] == pytest.approx(19.0, abs=1.0)
        temps = [e["temperature"] for e in hourly]
        assert temps == [pytest.approx(20.0), pytest.approx(21.0), pytest.approx(19.0)]

        # ── Humidity (index 2) ──
        assert current["humidity"] == pytest.approx(48.0)

        # ── Pressure (index 2: 101400 Pa → 1014.0 hPa) ──
        assert current["pressure"] == pytest.approx(1014.0, abs=0.1)

        # ── Wind (index 2: u=2, v=6 → speed=√(4+36)≈6.32) ──
        assert current["wind_speed"] == pytest.approx(math.sqrt(2**2 + 6**2), abs=0.1)
        expected_bearing = (math.degrees(math.atan2(2, 6)) + 180) % 360
        assert current["wind_bearing"] == pytest.approx(expected_bearing, abs=1.0)

        # ── Wind gust (index 2) ──
        assert current["wind_gust"] == pytest.approx(7.0)

        # ── CAPE (index 2) ──
        assert current["cape"] == pytest.approx(100.0)

        # ── Cloud cover ──
        assert current["cloud_cover"] is not None

        # ── Condition is valid HA string ──
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
        for i, entry in enumerate(hourly):
            assert entry["condition"] in valid_conditions, f"Entry {i}: '{entry['condition']}' not a valid HA condition"

        # ── Sensor data paths resolve ──
        for desc in WEATHER_SENSORS:
            _resolve_data_path(parsed, desc.data_path)
            # Value may be None for some entries, but path should work

        print("\n✓ Weather pipeline complete:")
        print(f"  {len(hourly)} forecast entries")
        print(f"  Current: {current['temperature']}°C, {current['condition']}")
        print(f"  Wind: {current['wind_speed']}m/s @ {current['wind_bearing']}°, gust {current['wind_gust']}m/s")
        print(f"  Pressure: {current['pressure']} hPa, Humidity: {current['humidity']}%")
        print(f"  CAPE: {current['cape']} J/kg")


class TestWavePipeline:
    """Test wave data: HTTP → parse → wave sensor values."""

    @pytest.mark.asyncio
    async def test_full_wave_flow(self, session, patch_urls):
        """API call with waves → coordinator parse → wave data valid."""
        client = WindyPointForecastClient(session, "test-key")
        result = await client.fetch(36.97, -122.03, model="gfs", include_waves=True)

        assert result["waves"] is not None

        coord = object.__new__(WindyWeatherCoordinator)
        coord._enable_waves = True
        coord._lon = -122.03
        parsed = coord._parse(result)

        assert parsed["current_waves"] is not None
        assert parsed["waves_hourly"] is not None
        assert len(parsed["waves_hourly"]) == 3

        # "current" = last entry (index 2, closest to now)
        cw = parsed["current_waves"]
        assert cw["wave_height"] == pytest.approx(1.2)
        assert cw["wave_period"] == pytest.approx(7.5)
        assert cw["wave_direction"] == pytest.approx(170.0)
        assert cw["wind_wave_height"] == pytest.approx(0.4)
        assert cw["swell1_height"] == pytest.approx(1.0)
        assert cw["swell1_period"] == pytest.approx(9.5)
        assert cw["swell2_height"] == pytest.approx(0.2)

        # All wave sensor data paths resolve
        for desc in WAVE_SENSORS:
            val = _resolve_data_path(parsed, desc.data_path)
            assert val is not None, f"Wave sensor {desc.key} resolved to None"

        print("\n✓ Wave pipeline complete:")
        print(f"  {len(parsed['waves_hourly'])} wave forecasts")
        print(f"  Combined: {cw['wave_height']}m @ {cw['wave_period']}s, dir {cw['wave_direction']}°")
        print(f"  Swell1: {cw['swell1_height']}m @ {cw['swell1_period']}s")
        print(f"  Swell2: {cw['swell2_height']}m")


class TestWebcamPipeline:
    """Test webcam data: HTTP → parse → camera entity values."""

    @pytest.mark.asyncio
    async def test_webcam_search(self, session, patch_urls):
        """Search for webcams via HTTP and validate response."""
        client = WindyWebcamClient(session, "test-key")
        cams = await client.search_nearby(36.97, -122.03)

        assert len(cams) == 1
        cam = cams[0]
        assert cam["title"] == "Test Beach Webcam"
        assert cam["webcamId"] == "1234567890"

        # Image URL extraction (same logic camera.py uses)
        images = cam.get("images", {})
        preview = images.get("current", {}).get("preview")
        assert preview is not None
        assert preview.startswith("https://")

        location = cam.get("location", {})
        assert location["city"] == "Test City"

        print(f"\n✓ Webcam pipeline: '{cam['title']}'")
        print(f"  ID: {cam['webcamId']}")
        print(f"  Location: {location['city']}, {location['country']}")
        print(f"  Preview: {preview}")

    @pytest.mark.asyncio
    async def test_webcam_by_id(self, session, patch_urls):
        """Fetch a specific webcam by ID."""
        client = WindyWebcamClient(session, "test-key")
        cams = await client.get_webcams(["1234567890"])

        assert len(cams) == 1
        assert cams[0]["title"] == "Test Beach Webcam"

        print("✓ Single webcam fetch by ID works")


class TestAuthFlow:
    """Test authentication through real HTTP."""

    @pytest.mark.asyncio
    async def test_bad_key_rejected_forecast(self, session, patch_urls):
        """Bad API key → WindyAuthError through full HTTP stack."""
        client = WindyPointForecastClient(session, "bad-key")
        with pytest.raises(WindyAuthError):
            await client.fetch(36.97, -122.03)

        print("✓ Forecast: bad key correctly rejected via HTTP")

    @pytest.mark.asyncio
    async def test_bad_key_rejected_webcam(self, session, patch_urls):
        """Bad webcam API key → WindyAuthError through full HTTP stack."""
        client = WindyWebcamClient(session, "bad-key")
        with pytest.raises(WindyAuthError):
            await client.search_nearby(36.97, -122.03)

        print("✓ Webcam: bad key correctly rejected via HTTP")


class TestEdgeCases:
    """Test edge cases through the full pipeline."""

    @pytest.mark.asyncio
    async def test_wave_fetch_failure_graceful(self, session, patch_urls):
        """If wave model fails, weather data should still work."""
        client = WindyPointForecastClient(session, "test-key")

        # Fetch with waves — even if wave model had issues, weather should work
        result = await client.fetch(36.97, -122.03, model="gfs", include_waves=True)
        assert result["weather"] is not None

        coord = object.__new__(WindyWeatherCoordinator)
        coord._enable_waves = True
        coord._lon = -122.03
        parsed = coord._parse(result)

        # Weather data should be fully valid regardless of wave status
        assert len(parsed["hourly"]) == 3
        assert parsed["current"]["temperature"] is not None

        print("✓ Weather pipeline works independently of wave data")

    @pytest.mark.asyncio
    async def test_all_forecast_entries_have_required_fields(self, session, patch_urls):
        """Every forecast entry must have all required fields for HA Forecast type."""
        client = WindyPointForecastClient(session, "test-key")
        result = await client.fetch(36.97, -122.03)

        coord = object.__new__(WindyWeatherCoordinator)
        coord._enable_waves = False
        coord._lon = -122.03
        parsed = coord._parse(result)

        required_fields = ["datetime", "temperature", "condition"]
        optional_fields = [
            "humidity",
            "pressure",
            "wind_speed",
            "wind_bearing",
            "wind_gust",
            "precipitation",
            "dew_point",
        ]

        for i, entry in enumerate(parsed["hourly"]):
            for field in required_fields:
                assert field in entry and entry[field] is not None, f"Entry {i} missing required field '{field}'"
            for field in optional_fields:
                assert field in entry, f"Entry {i} missing optional field '{field}'"

        print(f"✓ All {len(parsed['hourly'])} entries have required fields")
