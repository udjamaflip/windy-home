"""Tests for Windy API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.windy_home.api import (
    WindyApiError,
    WindyAuthError,
    WindyPointForecastClient,
    WindyWebcamClient,
)

from .conftest import MOCK_POINT_FORECAST_RESPONSE, MOCK_WEBCAM_RESPONSE


class TestPointForecastClient:
    """Test WindyPointForecastClient."""

    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    def _make_response(self, status=200, json_data=None, text=""):
        resp = AsyncMock()
        resp.status = status
        resp.json = AsyncMock(return_value=json_data or {})
        resp.text = AsyncMock(return_value=text)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)
        return resp

    @pytest.mark.asyncio
    async def test_fetch_weather_only(self, mock_session):
        resp = self._make_response(200, MOCK_POINT_FORECAST_RESPONSE)
        mock_session.post = MagicMock(return_value=resp)

        client = WindyPointForecastClient(mock_session, "test-key")
        result = await client.fetch(49.81, 16.79, model="gfs", include_waves=False)

        assert "weather" in result
        assert result["weather"] == MOCK_POINT_FORECAST_RESPONSE
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_with_waves(self, mock_session):
        resp1 = self._make_response(200, MOCK_POINT_FORECAST_RESPONSE)
        resp2 = self._make_response(200, {"ts": [1]})

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return resp1 if call_count == 1 else resp2

        mock_session.post = MagicMock(side_effect=side_effect)

        client = WindyPointForecastClient(mock_session, "test-key")
        result = await client.fetch(49.81, 16.79, include_waves=True)

        assert "weather" in result
        assert "waves" in result
        assert mock_session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_auth_error(self, mock_session):
        resp = self._make_response(401)
        mock_session.post = MagicMock(return_value=resp)

        client = WindyPointForecastClient(mock_session, "bad-key")
        with pytest.raises(WindyAuthError):
            await client.fetch(49.81, 16.79)

    @pytest.mark.asyncio
    async def test_bad_request(self, mock_session):
        resp = self._make_response(400, text="Invalid params")
        mock_session.post = MagicMock(return_value=resp)

        client = WindyPointForecastClient(mock_session, "test-key")
        with pytest.raises(WindyApiError, match="Bad request"):
            await client.fetch(49.81, 16.79)

    @pytest.mark.asyncio
    async def test_empty_model_response(self, mock_session):
        resp = self._make_response(204)
        mock_session.post = MagicMock(return_value=resp)

        client = WindyPointForecastClient(mock_session, "test-key")
        result = await client.fetch(49.81, 16.79)
        assert result["weather"] == {}

    @pytest.mark.asyncio
    async def test_validate_key_success(self, mock_session):
        resp = self._make_response(200, {"ts": [1]})
        mock_session.post = MagicMock(return_value=resp)

        client = WindyPointForecastClient(mock_session, "good-key")
        assert await client.validate_key() is True


class TestWebcamClient:
    """Test WindyWebcamClient."""

    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    def _make_response(self, status=200, json_data=None):
        resp = AsyncMock()
        resp.status = status
        resp.json = AsyncMock(return_value=json_data or {})
        resp.text = AsyncMock(return_value="")
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)
        return resp

    @pytest.mark.asyncio
    async def test_search_nearby(self, mock_session):
        resp = self._make_response(200, {"webcams": [MOCK_WEBCAM_RESPONSE]})
        mock_session.get = MagicMock(return_value=resp)

        client = WindyWebcamClient(mock_session, "test-key")
        cams = await client.search_nearby(40.0, -3.0)
        assert len(cams) == 1
        assert cams[0]["title"] == "Test Beach Webcam"

    @pytest.mark.asyncio
    async def test_get_webcams_empty(self, mock_session):
        client = WindyWebcamClient(mock_session, "test-key")
        result = await client.get_webcams([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_webcams_by_id(self, mock_session):
        resp = self._make_response(200, MOCK_WEBCAM_RESPONSE)
        mock_session.get = MagicMock(return_value=resp)

        client = WindyWebcamClient(mock_session, "test-key")
        result = await client.get_webcams(["1234567890"])
        assert len(result) == 1
