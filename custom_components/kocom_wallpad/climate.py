"""Climate platform for Kocom Wallpad."""
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
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
    """Set up Kocom climate."""
    coordinator: KocomCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    for device_str in coordinator.enabled_devices:
        if device_str.startswith("thermo_"):
            room = device_str.replace("thermo_", "")
            entities.append(KocomThermostat(coordinator, room))
    
    async_add_entities(entities)


class KocomThermostat(CoordinatorEntity, ClimateEntity):
    """Representation of a Kocom Thermostat."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_min_temp = 19
    _attr_max_temp = 25

    def __init__(self, coordinator: KocomCoordinator, room: str) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator)
        self._room = room
        self._device_key = f"thermo_{room}"
        
        room_names = {
            "livingroom": "거실",
            "bedroom": "안방",
            "room1": "서재",
            "room2": "작은방",
            "room3": "room3",
            "room4": "room4",
            "room5": "room5",
            "room6": "room6",
            "room7": "room7",
            "room8": "room8",
        }
        self._attr_name = f"{room_names.get(room, room)} 난방"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_thermo_{room}"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        data = self.coordinator.data.get(self._device_key, {})
        cur_temp = data.get("cur_temp")
        if cur_temp is None or cur_temp == 0:
            return None
        return float(cur_temp)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        data = self.coordinator.data.get(self._device_key, {})
        set_temp = data.get("set_temp")
        if set_temp is None:
            return float(self.coordinator.init_temp)
        return float(set_temp)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation mode."""
        data = self.coordinator.data.get(self._device_key, {})
        heat_mode = data.get("heat_mode", "off")
        return HVACMode.HEAT if heat_mode == "heat" else HVACMode.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        result = await self.coordinator.async_send_command(
            "thermo", self._room, "set_temp", temperature
        )
        
        if result:
            if self._device_key in self.coordinator.data:
                self.coordinator.data[self._device_key]["set_temp"] = int(temperature)
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        mode = "heat" if hvac_mode == HVACMode.HEAT else "off"
        result = await self.coordinator.async_send_command(
            "thermo", self._room, "heat_mode", mode
        )
        
        if result:
            if self._device_key in self.coordinator.data:
                self.coordinator.data[self._device_key]["heat_mode"] = mode
            self.async_write_ha_state()
