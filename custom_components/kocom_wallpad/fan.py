"""Fan platform for Kocom Wallpad."""
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FAN_PRESETS
from .coordinator import KocomCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kocom fan."""
    coordinator: KocomCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    if "fan" not in coordinator.enabled_devices:
        return
    
    async_add_entities([KocomFan(coordinator)])


class KocomFan(CoordinatorEntity, FanEntity):
    """Representation of a Kocom Fan."""

    _attr_supported_features = (
        FanEntityFeature.TURN_OFF |
        FanEntityFeature.TURN_ON |
        FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = FAN_PRESETS

    def __init__(self, coordinator: KocomCoordinator) -> None:
        """Initialize the fan."""
        super().__init__(coordinator)
        self._attr_name = "전열교환기"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_fan"

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        data = self.coordinator.data.get("fan", {})
        return data.get("state") == "on"

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        data = self.coordinator.data.get("fan", {})
        preset = data.get("preset", "Off")
        # Off 상태일 때는 None 반환
        return preset if preset != "Off" else None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        mode = preset_mode or self.coordinator.init_fan_mode
        result = await self.coordinator.async_send_command(
            "fan", "livingroom", "on", mode
        )
        
        if result:
            # 즉시 UI 상태 업데이트
            if "fan" in self.coordinator.data:
                self.coordinator.data["fan"]["state"] = "on"
                self.coordinator.data["fan"]["preset"] = mode
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        result = await self.coordinator.async_send_command(
            "fan", "livingroom", "off", "Off"
        )
        
        if result:
            # 즉시 UI 상태 업데이트
            if "fan" in self.coordinator.data:
                self.coordinator.data["fan"]["state"] = "off"
                self.coordinator.data["fan"]["preset"] = "Off"
            self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        result = await self.coordinator.async_send_command(
            "fan", "livingroom", "preset", preset_mode
        )
        
        if result:
            # 즉시 UI 상태 업데이트
            if "fan" in self.coordinator.data:
                self.coordinator.data["fan"]["state"] = "on" if preset_mode != "Off" else "off"
                self.coordinator.data["fan"]["preset"] = preset_mode
            self.async_write_ha_state()
