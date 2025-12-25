"""Light platform for Kocom Wallpad."""
import logging
from typing import Any

from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KocomCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kocom light."""
    coordinator: KocomCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    if not any(d.startswith("light") for d in coordinator.enabled_devices):
        return
    
    entities = []
    light_count = coordinator.light_count
    
    for i in range(1, light_count + 1):
        entities.append(KocomLight(coordinator, i))
    
    async_add_entities(entities)


class KocomLight(CoordinatorEntity, LightEntity):
    """Representation of a Kocom Light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator: KocomCoordinator, light_id: int) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._light_id = light_id
        self._attr_name = f"거실 조명 {light_id}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_light_{light_id}"

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        data = self.coordinator.data.get("light", {})
        return data.get(f"light_{self._light_id}") == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        result = await self.coordinator.async_send_command(
            "light", "livingroom", "on", {"light_id": self._light_id}
        )
        if result:
            # 즉시 UI 상태 업데이트
            if "light" in self.coordinator.data:
                self.coordinator.data["light"][f"light_{self._light_id}"] = "on"
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        result = await self.coordinator.async_send_command(
            "light", "livingroom", "off", {"light_id": self._light_id}
        )
        if result:
            # 즉시 UI 상태 업데이트
            if "light" in self.coordinator.data:
                self.coordinator.data["light"][f"light_{self._light_id}"] = "off"
            self.async_write_ha_state()
