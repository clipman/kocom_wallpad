"""Sensor platform for Kocom Wallpad."""
import logging

from homeassistant.components.sensor import SensorEntity
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
    """Set up Kocom sensor."""
    coordinator: KocomCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    if "elevator" in coordinator.enabled_devices:
        async_add_entities([KocomElevatorFloor(coordinator)])


class KocomElevatorFloor(CoordinatorEntity, SensorEntity):
    """Representation of Kocom Elevator Floor Sensor."""

    _attr_icon = "mdi:elevator"

    def __init__(self, coordinator: KocomCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "엘리베이터 층"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_elevator_floor"

    @property
    def native_value(self) -> int | None:
        """Return the elevator floor."""
        data = self.coordinator.data.get("elevator", {})
        return data.get("floor", self.coordinator.rs485_floor)
