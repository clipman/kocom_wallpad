"""Button platform for Kocom Wallpad."""
import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Kocom button."""
    coordinator: KocomCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([KocomQueryButton(coordinator)])


class KocomQueryButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Kocom Query Button."""

    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: KocomCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = "상태 업데이트"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_query"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Query button pressed - requesting refresh")
        try:
            await self.coordinator.async_send_query()
            _LOGGER.info("Query button refresh completed successfully")
        except Exception as e:
            _LOGGER.error(f"Query button refresh failed: {e}")
