"""Config flow for Kocom Wallpad integration."""
import voluptuous as vol
import socket
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_SOCKET_SERVER,
    CONF_SOCKET_PORT,
    CONF_RS485_FLOOR,
    CONF_LIGHT_COUNT,
    CONF_INIT_TEMP,
    CONF_INIT_FAN_MODE,
    CONF_ENABLED_DEVICES,
    DEFAULT_SOCKET_PORT,
    DEFAULT_RS485_FLOOR,
    DEFAULT_LIGHT_COUNT,
    DEFAULT_INIT_TEMP,
    DEFAULT_INIT_FAN_MODE,
    FAN_PRESETS,
)


class KocomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kocom Wallpad."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                await self._test_connection(
                    user_input[CONF_SOCKET_SERVER],
                    user_input[CONF_SOCKET_PORT]
                )
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Kocom Wallpad ({user_input[CONF_SOCKET_SERVER]})",
                    data=user_input
                )

        data_schema = vol.Schema({
            vol.Required(CONF_SOCKET_SERVER): str,
            vol.Required(CONF_SOCKET_PORT, default=DEFAULT_SOCKET_PORT): cv.port,
            vol.Required(CONF_RS485_FLOOR, default=DEFAULT_RS485_FLOOR): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=50)
            ),
            vol.Required(CONF_LIGHT_COUNT, default=DEFAULT_LIGHT_COUNT): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=8)
            ),
            vol.Required(CONF_INIT_TEMP, default=DEFAULT_INIT_TEMP): vol.All(
                vol.Coerce(int), vol.Range(min=15, max=30)
            ),
            vol.Required(CONF_INIT_FAN_MODE, default=DEFAULT_INIT_FAN_MODE): vol.In(
                [FAN_PRESETS[1], FAN_PRESETS[2], FAN_PRESETS[3]]
            ),
            vol.Required(CONF_ENABLED_DEVICES, default=[
                "light",
                "gas",
                "fan",
                "elevator",
                "thermo_livingroom",
                "thermo_bedroom",
                "thermo_room1",
                "thermo_room2",
            ]): cv.multi_select({
                "light": "거실 조명",
                "gas": "가스 차단",
                "fan": "전열교환기",
                "elevator": "엘리베이터",
                "thermo_livingroom": "거실 난방",
                "thermo_bedroom": "안방 난방",
                "thermo_room1": "서재 난방",
                "thermo_room2": "작은방 난방",
                "thermo_room3": "room3 난방",
                "thermo_room4": "room4 난방",
                "thermo_room5": "room5 난방",
                "thermo_room6": "room6 난방",
                "thermo_room7": "room7 난방",
                "thermo_room8": "room8 난방",
            }),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def _test_connection(self, host: str, port: int) -> bool:
        """Test if we can connect to the RS485 socket server."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            await self.hass.async_add_executor_job(sock.connect, (host, port))
            return True
        finally:
            sock.close()
