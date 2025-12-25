"""Coordinator for Kocom Wallpad integration."""
import asyncio
import logging
import socket
import time
from collections import deque
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_SOCKET_SERVER,
    CONF_SOCKET_PORT,
    CONF_RS485_FLOOR,
    CONF_LIGHT_COUNT,
    CONF_INIT_TEMP,
    CONF_INIT_FAN_MODE,
    CONF_ENABLED_DEVICES,
    DEFAULT_RS485_FLOOR,
    DEFAULT_LIGHT_COUNT,
    DEFAULT_INIT_TEMP,
    DEFAULT_INIT_FAN_MODE,
    DEFAULT_POLLING_INTERVAL,
    HEADER,
    TRAILER,
    PACKET_SIZE,
    CHKSUM_POSITION,
    READ_WRITE_GAP,
    DEVICE_WALLPAD,
    DEVICE_LIGHT,
    DEVICE_GAS,
    DEVICE_THERMO,
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    CMD_STATE,
    CMD_QUERY,
    TYPE_SEND,
    ROOM_LIVINGROOM,
    ROOM_NAMES,
    SEQ_CODES,
)

_LOGGER = logging.getLogger(__name__)


class KocomCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Kocom data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.config = entry.data
        self.socket_server = self.config[CONF_SOCKET_SERVER]
        self.socket_port = self.config[CONF_SOCKET_PORT]
        self.rs485_floor = self.config.get(CONF_RS485_FLOOR, DEFAULT_RS485_FLOOR)
        self.light_count = self.config.get(CONF_LIGHT_COUNT, DEFAULT_LIGHT_COUNT)
        self.init_temp = self.config.get(CONF_INIT_TEMP, DEFAULT_INIT_TEMP)
        self.init_fan_mode = self.config.get(CONF_INIT_FAN_MODE, DEFAULT_INIT_FAN_MODE)
        self.enabled_devices = self.config.get(CONF_ENABLED_DEVICES, [])
        
        self.sock = None
        self.last_read_time = 0
        self.send_lock = asyncio.Lock()
        self.cache_data = deque(maxlen=100)
        self.read_task = None

        # Initialize data dictionary
        self.data = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_POLLING_INTERVAL),
        )

    # async def _async_update_data(self) -> dict[str, Any]:
    #     """Fetch data from Kocom wallpad."""
    #     try:
    #         if not self.sock:
    #             await self._connect()
    #         data = {}
    #         for device_str in self.enabled_devices:
    #             parts = device_str.split("_")
    #             device_type = parts[0]
    #             room = parts[1] if len(parts) > 1 else "livingroom"
    #             device_id = self._get_device_id(device_type, room)
    #             if device_id:
    #                 result = await self._query_device(device_id)
    #                 _LOGGER.info(f"Query device: {device_id}, result: {result}")
    #                 if result:
    #                     data[device_str] = result
    #         return data
    #     except Exception as err:
    #         _LOGGER.error(f"Error updating data: {err}")
    #         await self._reconnect()
    #         raise UpdateFailed(f"Error communicating with device: {err}")

    # async def _async_update_data(self):
    #     _LOGGER.info("Polling interval reached - returning cached data")
    #     return self.data if hasattr(self, 'data') and self.data else {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Kocom wallpad."""
        try:
            if not self.sock:
                await self._connect()
                data = {}
                for device_str in self.enabled_devices:
                    parts = device_str.split("_")
                    device_type = parts[0]
                    room = parts[1] if len(parts) > 1 else "livingroom"
                    device_id = self._get_device_id(device_type, room)
                    if device_id:
                        result = await self._query_device(device_id)
                        _LOGGER.info(f"Query device: {device_id}, result: {result}")
                        if result:
                            data[device_str] = result
                return data
            else:
                _LOGGER.info("Polling interval reached - returning cached data")
                return self.data if hasattr(self, 'data') and self.data else {}
        except Exception as err:
            _LOGGER.error(f"Error updating data: {err}")
            await self._reconnect()
            raise UpdateFailed(f"Error communicating with device: {err}")

    async def _connect(self) -> None:
        """Connect to RS485 socket server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            await self.hass.async_add_executor_job(
                self.sock.connect, (self.socket_server, self.socket_port)
            )
            self.sock.settimeout(DEFAULT_POLLING_INTERVAL + 15)
            _LOGGER.info(f"Connected to {self.socket_server}:{self.socket_port}")
            
            if self.read_task is None or self.read_task.done():
                self.read_task = asyncio.create_task(self._read_loop())
        except Exception as e:
            _LOGGER.error(f"Connection error: {e}")
            raise

    async def _reconnect(self) -> None:
        """Reconnect to RS485 socket server."""
        await self._close()
        await asyncio.sleep(10)
        await self._connect()

    async def _close(self) -> None:
        """Close connection."""
        if self.read_task:
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
            self.read_task = None
        
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    async def _read_loop(self) -> None:
        """Continuously read from socket with improved stability."""
        buf = ""
        _LOGGER.info("Kocom read loop started")
        
        while True:
            try:
                if self.sock is None:
                    await asyncio.sleep(5)
                    continue

                # 비동기적으로 소켓 데이터 수신
                data = await self.hass.async_add_executor_job(self.sock.recv, 1024)
                if not data:
                    _LOGGER.warning("Socket connection lost. Reconnecting...")
                    await self._reconnect()
                    continue
                
                # 수신 데이터를 hex로 변환하여 버퍼에 추가
                buf += data.hex()
                self.last_read_time = time.time()

                # 헤더(aa55)를 찾을 때까지 앞부분 제거
                while len(buf) >= 4:
                    header_idx = buf.find(HEADER)
                    if header_idx == -1:
                        # 헤더가 없으면 마지막 2자(잠재적 헤더 시작)만 남기고 버림
                        buf = buf[-2:]
                        break
                    if header_idx > 0:
                        buf = buf[header_idx:]
                    
                    # 패킷 사이즈만큼 데이터가 쌓였는지 확인
                    if len(buf) >= PACKET_SIZE * 2:
                        packet = buf[:PACKET_SIZE * 2]
                        if self._validate_packet(packet):
                            # 유효한 패킷 처리 (await 추가)
                            await self._process_packet(packet)
                        
                        # 처리한 패킷만큼 버퍼에서 제거
                        buf = buf[PACKET_SIZE * 2:]
                    else:
                        break

            except socket.timeout:
                continue
            except Exception as e:
                # _LOGGER.error(f"Read error in loop: {e}")
                await asyncio.sleep(5)
                await self._reconnect()

    def _validate_packet(self, packet: str) -> bool:
        """Validate packet checksum and trailer."""
        chksum_calc = self._checksum(packet[len(HEADER):CHKSUM_POSITION*2])
        chksum_buf = packet[CHKSUM_POSITION*2:CHKSUM_POSITION*2+2]
        return (chksum_calc == chksum_buf and 
                packet[-len(TRAILER):] == TRAILER)

    async def _process_packet(self, packet: str) -> None:
        """Process received packet."""
        parsed = self._parse_packet(packet)
        self.cache_data.appendleft(parsed)
        _LOGGER.info(f"Received: {packet}, type: %s, src: %s, dest: %s", parsed["type"], parsed["src"], parsed["dest"])

        # UI/외부 장치에서 변경된 상태를 실시간으로 반영 (CMD_QUERY는 제외함, 난방도 제외함)
        # Received: aa5530dc00010036003a00000000000000007d0d0d, type: ack, src: 3600    -> x
        # Received: aa5530dc0001004800001100800000000000e60d0d, type: ack, src: 4800    -> o
        # Received: aa5530dc0001003602001100150015000000800d0d, type: ack, src: 3602    -> x
        # Received: aa5530dc0048000100001100800000000000e60d0d, type: ack, src: 0100    -> ?
        # Received: aa5530dc00360201000011001400150000007f0d0d, type: ack, src: 0100    -> ?
        # type_h = hex_data[4:7]        30d                 30dc                30dc
        # seq_h = hex_data[7:8]         c                   c                   c
        # dest_h = hex_data[10:14]      0100                0100                0100
        # src_h = hex_data[14:18]       3600                4800                3602
        # cmd_h = hex_data[18:20]       3a                  00                  00
        # value_h = hex_data[20:36]     0000000000000000    1100800000000000    1100150015000000
        # if parsed["type"] == "ack" and parsed["cmd"] != CMD_QUERY and parsed["src"] != DEVICE_WALLPAD + "00":
        # if parsed["type"] == "ack" and parsed["cmd"] != CMD_QUERY and parsed["src"] != DEVICE_WALLPAD + "00" and parsed["src"][:2] != DEVICE_THERMO:
        # if parsed["type"] == "ack" and parsed["cmd"] != CMD_QUERY and parsed["src"] == DEVICE_WALLPAD + "00":
        if parsed["type"] == "ack" and parsed["src"] == DEVICE_WALLPAD + "00":
            await self._update_state_from_packet(parsed)

    async def _update_state_from_packet(self, parsed: dict) -> None:
        """Update coordinator data from received packet."""
        dest_device = parsed["dest"][:2]
        device_id = parsed["dest"]
        updated = False

        if dest_device == DEVICE_LIGHT:
            device_key = "light"
            if device_key in self.enabled_devices:
                state = self._parse_value(device_id, parsed["value"])
                if state:
                    self.data[device_key] = state
                    updated = True

        elif dest_device == DEVICE_THERMO:
            room_code = device_id[2:4]
            room_name = None
            for name, code in ROOM_NAMES.items():
                if code == room_code:
                    room_name = name
                    break

            if room_name:
                device_key = f"thermo_{room_name}"
                if device_key in self.enabled_devices:
                    state = self._parse_value(device_id, parsed["value"])
                    if state:
                        self.data[device_key] = state
                        updated = True

        elif dest_device == DEVICE_FAN:
            device_key = "fan"
            if device_key in self.enabled_devices:
                state = self._parse_value(device_id, parsed["value"])
                if state:
                    self.data[device_key] = state
                    updated = True

        elif dest_device == DEVICE_GAS:
            device_key = "gas"
            if device_key in self.enabled_devices:
                state = self._parse_value(device_id, parsed["value"])
                if state:
                    self.data[device_key] = state
                    updated = True

        if updated:
            self.async_set_updated_data(self.data)
            _LOGGER.info(f"UI updated ({device_id}): {state}")

    def _parse_packet(self, hex_data: str) -> dict:
        """Parse hex packet."""
        type_h = hex_data[4:7]
        seq_h = hex_data[7:8]
        dest_h = hex_data[10:14]
        src_h = hex_data[14:18]
        cmd_h = hex_data[18:20]
        value_h = hex_data[20:36]
        
        # Determine packet type
        packet_type = "send" if type_h == TYPE_SEND else "ack"
        
        return {
            "type": packet_type,
            "seq": seq_h,
            "dest": dest_h,
            "src": src_h,
            "cmd": cmd_h,
            "value": value_h,
            "time": time.time(),
            "raw": hex_data,
        }

    async def _query_device(self, device_id: str) -> dict | None:
        """Query device state."""
        for item in self.cache_data:
            if time.time() - item["time"] > DEFAULT_POLLING_INTERVAL:
                break
            if item["type"] == "ack" and item["dest"] == device_id:
                return self._parse_value(device_id, item["value"])
        
        result = await self._send_command(device_id, CMD_QUERY)
        if result:
            return self._parse_value(device_id, result["value"])

        return None

    async def _send_command(
        self, dest: str, cmd: str, value: str = "0"*16, 
        src: str = DEVICE_WALLPAD + "00"
    ) -> dict | None:
        """Send command to device."""
        async with self.send_lock:
            for seq_h in SEQ_CODES.keys():
                payload = TYPE_SEND + seq_h + "00" + dest + src + cmd + value
                checksum = self._checksum(payload)
                packet = HEADER + payload + checksum + TRAILER
                
                if self.last_read_time > 0:
                    gap = time.time() - self.last_read_time
                    if gap < READ_WRITE_GAP:
                        await asyncio.sleep(READ_WRITE_GAP - gap)
                
                try:
                    await self.hass.async_add_executor_job(
                        self.sock.send, bytes.fromhex(packet)
                    )
                    # _LOGGER.info(f"Sent: {packet}")
                    
                    await asyncio.sleep(1.5)
                    
                    for item in reversed(list(self.cache_data)):
                        if item["dest"] == src and item["src"] == dest:
                            return item
                except Exception as e:
                    # _LOGGER.error(f"Send error: {e}")
                    break
        return None

    def _checksum(self, data_h: str) -> str:
        """Calculate checksum."""
        sum_buf = sum(bytes.fromhex(data_h))
        return f"{sum_buf % 256:02x}"

    def _get_device_id(self, device_type: str, room: str = "livingroom") -> str | None:
        """Get device ID from type and room."""
        device_map = {
            "light": DEVICE_LIGHT,
            "gas": DEVICE_GAS,
            "fan": DEVICE_FAN,
            "elevator": DEVICE_ELEVATOR,
            "thermo": DEVICE_THERMO,
        }
        
        device_code = device_map.get(device_type)
        if not device_code:
            return None
        
        room_code = ROOM_NAMES.get(room, ROOM_LIVINGROOM)
        return device_code + room_code

    def _parse_value(self, device_id: str, value: str) -> dict:
        """Parse device value."""
        device_type = device_id[:2]

        if device_type == DEVICE_THERMO:
            # value format: HHMM TT 00 CC 00000000
            # HH: heat mode (11=heat, 01=off)
            # MM: away mode
            # TT: set temp
            # CC: current temp
            # def thermo_parse(value):
            #     ret = { 'heat_mode': 'heat' if value[:2]=='11' else 'off',
            #             'away': 'true' if value[2:4]=='01' else 'false',
            #             'set_temp': int(value[4:6], 16) if value[:2]=='11' else int(config.get('User', 'init_temp')),
            #             'cur_temp': int(value[8:10], 16)}
            #     return ret
            heat_mode = "heat" if value[:2] == "11" else "off"
            set_temp = int(value[4:6], 16) if value[:2] == "11" else self.init_temp
            cur_temp = int(value[8:10], 16) if value[8:10] != "00" else None
            result = {
                "heat_mode": heat_mode,
                "set_temp": set_temp,
                "cur_temp": cur_temp,
                "value": value
            }
            return result

        elif device_type == DEVICE_LIGHT:
            result = {}
            for i in range(1, self.light_count + 1):
                result[f"light_{i}"] = "on" if value[i*2-2:i*2] != "00" else "off"
            return result

        elif device_type == DEVICE_FAN:
            preset_map = {"40": "Low", "80": "Medium", "c0": "High"}
            state = "on" if value[:2] == "11" else "off"
            preset = "Off" if state == "off" else preset_map.get(value[4:6], "Off")
            return {"state": state, "preset": preset}

        elif device_type == DEVICE_GAS:
            return {"state": "on"}

        return {}

    async def async_send_command(
        self, device_type: str, room: str, command: str, 
        value: Any = None
    ) -> bool:
        """Send command to device."""
        device_id = self._get_device_id(device_type, room)
        if not device_id:
            return False
        
        cmd_value = self._build_command_value(device_type, command, value, device_id)
        if not cmd_value:
            return False
        
        result = await self._send_command(device_id, CMD_STATE, cmd_value)
        _LOGGER.info(f"Sent Command Device: {device_id}, Value: {cmd_value}")
        return result is not None

    def _build_command_value(
        self, device_type: str, command: str, value: Any, device_id: str
    ) -> str | None:
        """Build command value hex string by patching existing values."""

        if device_type == "light":
            hex_value = "0" * 16
            if isinstance(value, dict) and "light_id" in value:
                light_id = value["light_id"]
                onoff = "ff" if command == "on" else "00"
                pos = light_id * 2 - 2
                hex_value = hex_value[:pos] + onoff + hex_value[pos+2:]
            return hex_value

        elif device_type == "thermo":
            room_name = next((name for name, code in ROOM_NAMES.items() if code == device_id[2:4]), None)
            device_key = f"thermo_{room_name}"
            # if device_key not in self.data:
            #     self.data[device_key].set("value", "0100050014000000") # 기본값
            # current_raw = self.data[device_key].get("value")
            current_raw = self.data[device_key].get("value", "0100050014000000")
            if command == "heat_mode":
                new_mode = "11" if value == "heat" else "01"
                temp = f"{self.init_temp:02x}"
                # 앞 4자리(모드+00) + 초기값 온도(2자리) + 나머지 10자리 유지
                return new_mode + "00" + temp + current_raw[6:]
            elif command == "set_temp":
                new_temp = f"{int(value):02x}"
                # 앞 4자리(모드+00) 유지 + 새로운 온도(2자리) + 나머지 10자리 유지
                return current_raw[:4] + new_temp + current_raw[6:]
            return current_raw

        elif device_type == "fan":
            speed_map = {"Off": "00", "Low": "40", "Medium": "80", "High": "c0"}
            onoff = "1000" if value == "Off" else "1100"
            speed = speed_map.get(value, "80")
            return onoff + speed + "0" * 10

        elif device_type == "gas" and command == "off":
            return "0" * 16
        
        elif device_type == "elevator" and command == "on":
            return "0" * 16

        return None

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        await self._close()

    async def async_send_query(self) -> None:
        """Send query."""
        _LOGGER.info("Send query started")
        try:
            if not self.sock:
                await self._connect()

            for device_str in self.enabled_devices:
                parts = device_str.split("_")
                device_type = parts[0]
                room = parts[1] if len(parts) > 1 else "livingroom"

                device_id = self._get_device_id(device_type, room)
                if device_id:
                    await self._send_command(device_id, CMD_QUERY)
        except Exception as err:
            _LOGGER.error(f"Error query data: {err}")
            await self._reconnect()
            raise UpdateFailed(f"Error communicating with device: {err}")
