"""Fixtures for Windy Home tests."""

from __future__ import annotations

import asyncio
import sys

import pytest

if sys.platform == "win32":

    @pytest.fixture
    def event_loop():
        """Use SelectorEventLoop on Windows for asyncio compatibility."""
        loop = asyncio.SelectorEventLoop()
        yield loop
        loop.close()


MOCK_POINT_FORECAST_RESPONSE = {
    "ts": [
        1700000000000,
        1700010800000,
        1700021600000,
    ],
    "units": {
        "temp-surface": "K",
        "wind_u-surface": "m/s",
        "wind_v-surface": "m/s",
    },
    "temp-surface": [293.15, 294.15, 292.15],  # 20°C, 21°C, 19°C
    "dewpoint-surface": [283.15, 284.15, 282.15],  # 10°C, 11°C, 9°C
    "rh-surface": [52.0, 55.0, 48.0],
    "pressure-surface": [101325.0, 101200.0, 101400.0],  # Pa
    "wind_u-surface": [3.0, 5.0, 2.0],
    "wind_v-surface": [4.0, 3.0, 6.0],
    "gust-surface": [8.0, 10.0, 7.0],
    "past3hprecip-surface": [0.0, 1.5, 0.0],
    "past3hconvprecip-surface": [0.0, 0.5, 0.0],
    "cape-surface": [200.0, 1500.0, 100.0],
    "lclouds-surface": [10.0, 80.0, 5.0],
    "mclouds-surface": [20.0, 60.0, 10.0],
    "hclouds-surface": [5.0, 30.0, 0.0],
    "ptype-surface": [0.0, 1.0, 0.0],
}

MOCK_WAVE_RESPONSE = {
    "ts": [
        1700000000000,
        1700010800000,
        1700021600000,
    ],
    "waves_height-surface": [1.5, 2.0, 1.2],
    "waves_period-surface": [8.0, 9.0, 7.5],
    "waves_direction-surface": [180.0, 190.0, 170.0],
    "windWaves_height-surface": [0.5, 0.8, 0.4],
    "windWaves_period-surface": [4.0, 4.5, 3.5],
    "windWaves_direction-surface": [200.0, 210.0, 195.0],
    "swell1_height-surface": [1.2, 1.5, 1.0],
    "swell1_period-surface": [10.0, 11.0, 9.5],
    "swell1_direction-surface": [170.0, 175.0, 165.0],
    "swell2_height-surface": [0.3, 0.4, 0.2],
    "swell2_period-surface": [6.0, 6.5, 5.5],
    "swell2_direction-surface": [250.0, 255.0, 245.0],
}

MOCK_WEBCAM_RESPONSE = {
    "webcamId": "1234567890",
    "title": "Test Beach Webcam",
    "location": {
        "city": "Test City",
        "region": "Test Region",
        "country": "Test Country",
        "latitude": 40.0,
        "longitude": -3.0,
    },
    "images": {
        "current": {
            "preview": "https://images.windy.com/test/preview.jpg",
            "thumbnail": "https://images.windy.com/test/thumb.jpg",
        },
    },
}
