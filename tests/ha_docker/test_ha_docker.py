"""
Docker-based integration test for Windy Home.

Spins up a real Home Assistant instance in Docker, verifies:
  1. HA starts healthy with our integration mounted
  2. The integration appears in the component list
  3. Config flow can be initiated
  4. A config entry can be created (with a test key — will fail auth but proves the flow runs)
  5. The integration creates the expected platforms

Requires: Docker running, port 18123 free.

Run automated:
    python -m pytest tests/ha_docker/test_ha_docker.py -v -s --timeout=180

Or via the launcher:
    python tests/ha_docker/run_ha.py test

The container is left running after tests so you can open
http://localhost:18123 in a browser and interact with HA manually.
Stop with:  python tests/ha_docker/run_ha.py stop
"""

from __future__ import annotations

import os
import subprocess
import time

import aiohttp
import pytest

HA_URL = "http://localhost:18123"
COMPOSE_DIR = os.path.dirname(__file__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run docker compose in the ha_docker directory."""
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=COMPOSE_DIR,
        capture_output=True,
        text=True,
        check=check,
    )


def _wait_for_ha(timeout: int = 120) -> bool:
    """Block until HA answers on /api/ or timeout."""
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = urllib.request.urlopen(f"{HA_URL}/api/", timeout=3)
            if r.status == 200:
                return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    return False


# ---------------------------------------------------------------------------
# Onboarding helper — HA 2024.x requires onboarding before API works
# ---------------------------------------------------------------------------


async def _onboard(session: aiohttp.ClientSession) -> str:
    """Complete HA onboarding and return a long-lived access token."""

    # Step 1: create owner account
    async with session.post(
        f"{HA_URL}/api/onboarding/users",
        json={
            "client_id": HA_URL,
            "name": "Test",
            "username": "test",
            "password": "testtest1",
            "language": "en",
        },
    ) as resp:
        data = await resp.json()
        auth_code = data.get("auth_code")

    # Step 2: exchange auth code for tokens
    async with session.post(
        f"{HA_URL}/auth/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": HA_URL,
        },
    ) as resp:
        tokens = await resp.json()
        access_token = tokens["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # Step 3: finish remaining onboarding steps
    for step in ("core_config", "analytics", "integration"):
        async with session.post(
            f"{HA_URL}/api/onboarding/{step}",
            headers=headers,
            json={},
        ) as resp:
            pass  # ignore errors on already-completed steps

    return access_token


async def _login(session: aiohttp.ClientSession) -> str:
    """Log in to an already-onboarded HA and return an access token."""
    # Start an auth flow
    async with session.post(
        f"{HA_URL}/auth/login_flow",
        json={"client_id": HA_URL, "handler": ["homeassistant", None]},
    ) as resp:
        flow = await resp.json()
        flow_id = flow["flow_id"]

    # Submit credentials
    async with session.post(
        f"{HA_URL}/auth/login_flow/{flow_id}",
        json={"username": "test", "password": "testtest1", "client_id": HA_URL},
    ) as resp:
        result = await resp.json()
        auth_code = result.get("result")

    # Exchange for token
    async with session.post(
        f"{HA_URL}/auth/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": HA_URL,
        },
    ) as resp:
        tokens = await resp.json()
        return tokens["access_token"]


async def _get_or_create_auth(session: aiohttp.ClientSession) -> str:
    """Get an auth token — onboard if fresh, log in if already set up."""
    # Check onboarding status
    async with session.get(f"{HA_URL}/api/onboarding") as resp:
        steps = await resp.json()

    done_steps = {s["step"] for s in steps if s["done"]}

    if "user" not in done_steps:
        # Fresh instance — run full onboarding
        return await _onboard(session)
    else:
        # Already onboarded — just log in
        return await _login(session)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ha_container():
    """Ensure HA container is running. Leaves it up after tests for manual use."""
    # Check if already running
    result = _compose("ps", "--format", "{{.Status}}", check=False)
    already_running = "Up" in (result.stdout or "")

    if not already_running:
        # Clean up orphans from a bad previous state
        _compose("down", "--remove-orphans", check=False)

        # Start fresh
        result = _compose("up", "-d")
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            pytest.fail(f"docker compose up failed: {result.stderr}")

    # Wait for HA to be ready
    if not _wait_for_ha(timeout=180):
        logs = _compose("logs", "--tail=80", check=False)
        print(logs.stdout[-3000:] if logs.stdout else "no logs")
        pytest.fail("Home Assistant did not start within 180s")

    yield

    # Intentionally do NOT tear down — leave running for manual testing.
    # User can stop with: python tests/ha_docker/run_ha.py stop


@pytest.fixture(scope="module")
async def ha_session(ha_container):
    """Onboard HA (if needed) and return (session, headers) with auth."""
    async with aiohttp.ClientSession() as session:
        token = await _get_or_create_auth(session)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        yield session, headers


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHomeAssistantDocker:
    """Integration tests against a real HA instance."""

    @pytest.mark.asyncio
    async def test_ha_is_running(self, ha_session):
        """HA responds to API calls."""
        session, headers = ha_session
        async with session.get(f"{HA_URL}/api/", headers=headers) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["message"] == "API running."

    @pytest.mark.asyncio
    async def test_integration_discovered(self, ha_session):
        """windy_home appears in the list of custom components."""
        session, headers = ha_session

        # HA loads custom_components at startup; verify via /api/services or config/entries
        # Check that the config flow is available
        async with session.get(
            f"{HA_URL}/api/config/config_entries/flow_handlers",
            headers=headers,
        ) as resp:
            assert resp.status == 200
            handlers = await resp.json()
            assert "windy_home" in handlers, f"windy_home not in flow handlers: {handlers[:20]}..."

    @pytest.mark.asyncio
    async def test_config_flow_starts(self, ha_session):
        """The config flow can be initiated through the API."""
        session, headers = ha_session

        # Start the config flow
        async with session.post(
            f"{HA_URL}/api/config/config_entries/flow",
            headers=headers,
            json={"handler": "windy_home", "show_advanced_options": False},
        ) as resp:
            assert resp.status == 200
            flow = await resp.json()
            assert flow["type"] == "form"
            assert flow["step_id"] == "user"

            # Verify form has expected fields
            schema_keys = [s["name"] for s in flow.get("data_schema", [])]
            assert "api_key" in schema_keys
            assert "latitude" in schema_keys
            assert "longitude" in schema_keys
            assert "forecast_model" in schema_keys

            flow_id = flow["flow_id"]

        # Clean up — abort the flow
        async with session.delete(
            f"{HA_URL}/api/config/config_entries/flow/{flow_id}",
            headers=headers,
        ) as resp:
            pass

    @pytest.mark.asyncio
    async def test_config_flow_rejects_bad_key(self, ha_session):
        """Submitting a bad API key returns an auth error, not a crash."""
        session, headers = ha_session

        # Start flow
        async with session.post(
            f"{HA_URL}/api/config/config_entries/flow",
            headers=headers,
            json={"handler": "windy_home"},
        ) as resp:
            flow = await resp.json()
            flow_id = flow["flow_id"]

        # Submit with a fake key — should get invalid_auth error, not 500
        async with session.post(
            f"{HA_URL}/api/config/config_entries/flow/{flow_id}",
            headers=headers,
            json={
                "api_key": "fake-key-12345",
                "location_name": "Test",
                "latitude": 51.5,
                "longitude": -0.1,
                "forecast_model": "gfs",
                "enable_waves": False,
            },
        ) as resp:
            assert resp.status == 200
            result = await resp.json()
            # Should be a form with errors, not "create_entry" or a crash
            assert result["type"] == "form", f"Unexpected type: {result}"
            errors = result.get("errors", {})
            assert errors.get("base") in ("invalid_auth", "cannot_connect"), (
                f"Expected auth/connect error, got: {errors}"
            )

    @pytest.mark.asyncio
    async def test_config_flow_creates_entry_with_real_key(self, ha_session):
        """If WINDY_API_KEY env var is set, create a real config entry."""
        api_key = os.environ.get("WINDY_API_KEY")
        if not api_key:
            pytest.skip("Set WINDY_API_KEY to run this test")

        session, headers = ha_session

        # Start flow
        async with session.post(
            f"{HA_URL}/api/config/config_entries/flow",
            headers=headers,
            json={"handler": "windy_home"},
        ) as resp:
            flow = await resp.json()
            flow_id = flow["flow_id"]

        # Submit with real key
        async with session.post(
            f"{HA_URL}/api/config/config_entries/flow/{flow_id}",
            headers=headers,
            json={
                "api_key": api_key,
                "location_name": "Docker Test",
                "latitude": 51.5,
                "longitude": -0.1,
                "forecast_model": "gfs",
                "enable_waves": False,
            },
        ) as resp:
            result = await resp.json()
            assert result["type"] == "create_entry", f"Flow didn't complete: {result}"
            assert result["title"] == "Docker Test"

        # Verify the entry exists
        async with session.get(
            f"{HA_URL}/api/config/config_entries",
            headers=headers,
        ) as resp:
            entries = await resp.json()
            windy_entries = [e for e in entries if e["domain"] == "windy_home"]
            assert len(windy_entries) == 1

        # Give HA a moment to set up platforms, then check states
        await _async_sleep(5)

        async with session.get(
            f"{HA_URL}/api/states",
            headers=headers,
        ) as resp:
            states = await resp.json()
            windy_entities = [
                s
                for s in states
                if s["entity_id"].startswith("weather.windy") or s["entity_id"].startswith("sensor.windy")
            ]
            assert len(windy_entities) > 0, "No windy entities found after setup"
            print(f"\n  Created {len(windy_entities)} entities:")
            for e in windy_entities:
                print(f"    {e['entity_id']}: {e['state']}")


async def _async_sleep(seconds: float) -> None:
    """Async sleep helper."""
    import asyncio

    await asyncio.sleep(seconds)
