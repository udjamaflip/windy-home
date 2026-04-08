"""Base entity for Windy Home integration."""

from __future__ import annotations

try:
    from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
except ImportError:
    from homeassistant.helpers.device_registry import DeviceEntryType
    from homeassistant.helpers.entity import DeviceInfo

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN


class WindyHomeEntity(CoordinatorEntity):
    """Base class for Windy Home entities."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Windy.com",
            model="Point Forecast API",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://api.windy.com/keys",
        )
