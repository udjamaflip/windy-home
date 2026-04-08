"""Async API client for Windy Point Forecast v2 and Webcams v3."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    FORECAST_PARAMS,
    WAVE_PARAMS,
    WINDY_POINT_FORECAST_URL,
    WINDY_WEBCAM_API_URL,
)

_LOGGER = logging.getLogger(__name__)


class WindyApiError(Exception):
    """Base exception for Windy API errors."""


class WindyAuthError(WindyApiError):
    """Raised when the API key is invalid."""


class WindyConnectionError(WindyApiError):
    """Raised when a connection error occurs."""


class WindyPointForecastClient:
    """Client for Windy Point Forecast API v2."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
    ) -> None:
        self._session = session
        self._api_key = api_key

    async def fetch(
        self,
        lat: float,
        lon: float,
        model: str = "gfs",
        include_waves: bool = False,
    ) -> dict[str, Any]:
        """Fetch point forecast from Windy API.

        Returns raw response dict with timestamp array and parameter arrays.
        """
        params = list(FORECAST_PARAMS)
        request_model = model

        payload: dict[str, Any] = {
            "lat": round(lat, 2),
            "lon": round(lon, 2),
            "model": request_model,
            "parameters": params,
            "levels": ["surface"],
            "key": self._api_key,
        }

        result: dict[str, Any] = {}

        # Fetch weather forecast
        result["weather"] = await self._post(payload)

        # If waves requested, fetch from gfsWave model separately
        if include_waves:
            wave_payload: dict[str, Any] = {
                "lat": round(lat, 2),
                "lon": round(lon, 2),
                "model": "gfsWave",
                "parameters": list(WAVE_PARAMS),
                "levels": ["surface"],
                "key": self._api_key,
            }
            try:
                result["waves"] = await self._post(wave_payload)
            except WindyApiError:
                _LOGGER.warning("Failed to fetch wave data; skipping")
                result["waves"] = None

        return result

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request to the Point Forecast API."""
        try:
            async with self._session.post(
                WINDY_POINT_FORECAST_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 401 or resp.status == 403:
                    raise WindyAuthError("Invalid API key")
                if resp.status == 400:
                    text = await resp.text()
                    raise WindyApiError(f"Bad request: {text}")
                if resp.status == 204:
                    return {}
                if resp.status != 200:
                    text = await resp.text()
                    raise WindyApiError(f"Unexpected status {resp.status}: {text}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise WindyConnectionError(f"Connection error: {err}") from err

    async def validate_key(self, lat: float = 49.81, lon: float = 16.79) -> bool:
        """Validate the API key with a minimal request."""
        payload = {
            "lat": lat,
            "lon": lon,
            "model": "gfs",
            "parameters": ["temp"],
            "levels": ["surface"],
            "key": self._api_key,
        }
        await self._post(payload)
        return True


class WindyWebcamClient:
    """Client for Windy Webcams API v3."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
    ) -> None:
        self._session = session
        self._api_key = api_key

    async def search_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: int = 50,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for webcams near a coordinate."""
        params = {
            "nearby": f"{lat},{lon},{radius_km}",
            "limit": str(limit),
            "include": "images,location",
        }
        return await self._get(params)

    async def get_webcams(self, webcam_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch specific webcams by ID."""
        if not webcam_ids:
            return []

        results: list[dict[str, Any]] = []
        # API accepts individual webcam fetch
        for wid in webcam_ids:
            try:
                async with self._session.get(
                    f"{WINDY_WEBCAM_API_URL}/{wid}",
                    headers={"x-windy-api-key": self._api_key},
                    params={"include": "images,location"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results.append(data)
                    else:
                        _LOGGER.warning(
                            "Failed to fetch webcam %s: HTTP %s",
                            wid,
                            resp.status,
                        )
            except aiohttp.ClientError as err:
                _LOGGER.warning("Error fetching webcam %s: %s", wid, err)
        return results

    async def _get(self, params: dict[str, str]) -> list[dict[str, Any]]:
        """Make a GET request to the Webcams API."""
        try:
            async with self._session.get(
                WINDY_WEBCAM_API_URL,
                headers={"x-windy-api-key": self._api_key},
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401 or resp.status == 403:
                    raise WindyAuthError("Invalid API key for webcams")
                if resp.status != 200:
                    text = await resp.text()
                    raise WindyApiError(f"Webcam API error {resp.status}: {text}")
                data = await resp.json()
                return data.get("webcams", [])
        except aiohttp.ClientError as err:
            raise WindyConnectionError(f"Webcam connection error: {err}") from err
