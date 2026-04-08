"""The Windy Home integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WindyPointForecastClient, WindyWebcamClient
from .const import (
    CONF_ENABLE_WAVES,
    CONF_FORECAST_MODEL,
    CONF_UPDATE_INTERVAL,
    CONF_WEBCAM_API_KEY,
    CONF_WEBCAM_IDS,
    DEFAULT_FORECAST_MODEL,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_WEBCAM_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import WindyWeatherCoordinator, WindyWebcamCoordinator

_LOGGER = logging.getLogger(__name__)

CARDS_URL = f"/{DOMAIN}/windy-cards.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the static path for Windy frontend cards."""
    www = Path(__file__).parent / "www"
    if www.is_dir():
        try:
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARDS_URL, str(www / "windy-cards.js"), True)]
            )
        except (ImportError, AttributeError):
            hass.http.register_static_path(CARDS_URL, str(www / "windy-cards.js"), True)

        # Ensure the JS is registered as a Lovelace resource (storage-based)
        await _async_ensure_lovelace_resource(hass)
    return True


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Add the Windy cards JS to Lovelace resources via the HA store."""
    from homeassistant.helpers.storage import Store

    store = Store(hass, 1, "lovelace_resources")
    resource_entry = {
        "id": "windy_home_cards",
        "type": "module",
        "url": CARDS_URL,
    }

    try:
        data = await store.async_load()
        if data is None:
            data = {"items": [resource_entry]}
        else:
            items = data.get("items", [])
            for item in items:
                if CARDS_URL in item.get("url", ""):
                    return
            items.append(resource_entry)
            data["items"] = items

        await store.async_save(data)
        _LOGGER.info("Registered Windy cards as Lovelace resource: %s", CARDS_URL)
    except Exception:
        _LOGGER.warning(
            "Could not auto-register Lovelace resource. "
            "Add manually: Settings → Dashboards → Resources → %s (JavaScript Module)",
            CARDS_URL,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Windy Home from a config entry."""
    session = async_get_clientsession(hass)
    api_key = entry.data[CONF_API_KEY]
    lat = entry.data[CONF_LATITUDE]
    lon = entry.data[CONF_LONGITUDE]

    # Merge options over data for runtime config
    model = entry.options.get(
        CONF_FORECAST_MODEL,
        entry.data.get(CONF_FORECAST_MODEL, DEFAULT_FORECAST_MODEL),
    )
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    enable_waves = entry.options.get(CONF_ENABLE_WAVES, entry.data.get(CONF_ENABLE_WAVES, False))

    # Create API clients
    forecast_client = WindyPointForecastClient(session, api_key)

    # Webcam client uses a separate API key (Windy issues per-service keys)
    webcam_api_key = entry.options.get(CONF_WEBCAM_API_KEY) or entry.data.get(CONF_WEBCAM_API_KEY) or ""
    webcam_client = WindyWebcamClient(session, webcam_api_key) if webcam_api_key else None

    # Weather coordinator
    weather_coordinator = WindyWeatherCoordinator(
        hass,
        entry,
        forecast_client,
        lat=lat,
        lon=lon,
        model=model,
        enable_waves=enable_waves,
        update_interval_min=update_interval,
    )
    await weather_coordinator.async_config_entry_first_refresh()

    # Webcam coordinator (only if webcam IDs configured)
    webcam_ids_raw = entry.options.get(CONF_WEBCAM_IDS, entry.data.get(CONF_WEBCAM_IDS, ""))
    webcam_ids = [wid.strip() for wid in webcam_ids_raw.split(",") if wid.strip()] if webcam_ids_raw else []

    webcam_coordinator = None
    if webcam_ids and webcam_client:
        webcam_coordinator = WindyWebcamCoordinator(
            hass,
            entry,
            webcam_client,
            webcam_ids=webcam_ids,
            update_interval_min=DEFAULT_WEBCAM_UPDATE_INTERVAL,
        )
        await webcam_coordinator.async_config_entry_first_refresh()

    # Store in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "weather_coordinator": weather_coordinator,
        "webcam_coordinator": webcam_coordinator,
        "forecast_client": forecast_client,
        "webcam_client": webcam_client,
    }

    # Forward platform setup
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates to reload
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Windy Home config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
    return unload_ok
