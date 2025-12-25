"""Switch platform for Kocom Wallpad."""
import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up Kocom switch."""
    coordinator: KocomCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    if "gas" in coordinator.enabled_devices:
        entities.append(KocomGas(coordinator))
    
    if "elevator" in coordinator.enabled_devices:
        entities.append(KocomElevator(coordinator))
    
    async_add_entities(entities)


class KocomGas(CoordinatorEntity, SwitchEntity):
    """Representation of a Kocom Gas Valve."""

    _attr_icon = "mdi:gas-cylinder"

    def __init__(self, coordinator: KocomCoordinator) -> None:
        """Initialize the gas valve."""
        super().__init__(coordinator)
        self._attr_name = "거실 가스 차단"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_gas"

    @property
    def is_on(self) -> bool:
        """Return true if valve is on (open)."""
        data = self.coordinator.data.get("gas", {})
        return data.get("state") == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the valve on (open) - not supported."""
        _LOGGER.warning("Cannot turn on gas valve")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the valve off (close)."""
        result = await self.coordinator.async_send_command(
            "gas", "livingroom", "off"
        )
        if result:
            # 즉시 UI 상태 업데이트
            if "gas" in self.coordinator.data:
                self.coordinator.data["gas"]["state"] = "off"
            self.async_write_ha_state()


class KocomElevator(CoordinatorEntity, SwitchEntity):
    """Representation of a Kocom Elevator Call."""

    _attr_icon = "mdi:elevator"

    def __init__(self, coordinator: KocomCoordinator) -> None:
        """Initialize the elevator."""
        super().__init__(coordinator)
        self._attr_name = "엘리베이터 호출"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_elevator"
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return state."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Call elevator."""
        result = await self.coordinator.async_send_command(
            "elevator", "myhome", "on"
        )
        if result:
            self._is_on = True
            self.async_write_ha_state()
            await asyncio.sleep(5)
            self._is_on = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off - just update state."""
        self._is_on = False
        self.async_write_ha_state()
