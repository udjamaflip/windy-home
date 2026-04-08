"""Camera platform for Windy Home — webcam entities."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_WEBCAM_IDS, DOMAIN
from .entity import WindyHomeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Windy webcam camera entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    webcam_coordinator = data.get("webcam_coordinator")

    if webcam_coordinator is None:
        return

    webcam_ids = _get_webcam_ids(config_entry)
    if not webcam_ids:
        return

    entities: list[WindyWebcamCamera] = []
    for i, webcam_data in enumerate(webcam_coordinator.data or []):
        webcam_id = webcam_data.get("webcamId") or webcam_data.get("id", str(i))
        entities.append(WindyWebcamCamera(webcam_coordinator, config_entry, webcam_id, webcam_data, i))

    async_add_entities(entities)


def _get_webcam_ids(config_entry: ConfigEntry) -> list[str]:
    """Extract webcam IDs from config entry."""
    raw = config_entry.options.get(CONF_WEBCAM_IDS, config_entry.data.get(CONF_WEBCAM_IDS, ""))
    if not raw:
        return []
    return [wid.strip() for wid in raw.split(",") if wid.strip()]


class WindyWebcamCamera(WindyHomeEntity, Camera):
    """A Windy webcam as a Home Assistant camera."""

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        webcam_id: str,
        webcam_data: dict[str, Any],
        index: int,
    ) -> None:
        super().__init__(coordinator, config_entry)
        Camera.__init__(self)
        self._webcam_id = webcam_id
        self._index = index
        self._attr_unique_id = f"{config_entry.entry_id}_webcam_{webcam_id}"
        title = webcam_data.get("title", f"Webcam {webcam_id}")
        self._attr_name = title

        location = webcam_data.get("location", {})
        self._attr_extra_state_attributes = {
            "webcam_id": webcam_id,
            "city": location.get("city"),
            "region": location.get("region"),
            "country": location.get("country"),
        }

    def _current_webcam_data(self) -> dict[str, Any] | None:
        """Get current webcam data from coordinator."""
        if not self.coordinator.data:
            return None
        for cam in self.coordinator.data:
            cid = cam.get("webcamId") or cam.get("id")
            if str(cid) == str(self._webcam_id):
                return cam
        # Fall back to index
        if self._index < len(self.coordinator.data):
            return self.coordinator.data[self._index]
        return None

    def _get_image_url(self) -> str | None:
        """Extract the preview image URL from webcam data."""
        cam = self._current_webcam_data()
        if not cam:
            return None
        images = cam.get("images", {})
        # Try current preview first, then daylight, then any available
        for key in ("current", "daylight"):
            img = images.get(key, {})
            preview = img.get("preview") or img.get("thumbnail")
            if preview:
                return preview
        return None

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return the webcam preview image."""
        url = self._get_image_url()
        if not url:
            return None
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.read()
                _LOGGER.warning(
                    "Webcam image fetch failed for %s: HTTP %s",
                    self._webcam_id,
                    resp.status,
                )
        except aiohttp.ClientError as err:
            _LOGGER.warning("Webcam image error for %s: %s", self._webcam_id, err)
        return None
