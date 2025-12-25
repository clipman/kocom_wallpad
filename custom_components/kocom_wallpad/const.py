"""Constants for Kocom Wallpad integration."""

DOMAIN = "kocom_wallpad"

# Config Flow
CONF_SOCKET_SERVER = "socket_server"
CONF_SOCKET_PORT = "socket_port"
CONF_RS485_FLOOR = "rs485_floor"
CONF_LIGHT_COUNT = "light_count"
CONF_INIT_TEMP = "init_temp"
CONF_INIT_FAN_MODE = "init_fan_mode"
CONF_ENABLED_DEVICES = "enabled_devices"

# Defaults
DEFAULT_SOCKET_PORT = 8899
DEFAULT_RS485_FLOOR = 15
DEFAULT_LIGHT_COUNT = 2
DEFAULT_INIT_TEMP = 20
DEFAULT_INIT_FAN_MODE = "Medium"
DEFAULT_POLLING_INTERVAL = 300

# Protocol Constants
HEADER = "aa55"
TRAILER = "0d0d"
PACKET_SIZE = 21
CHKSUM_POSITION = 18
READ_WRITE_GAP = 0.03

# Device Types
DEVICE_WALLPAD = "01"
DEVICE_LIGHT = "0e"
DEVICE_GAS = "2c"
DEVICE_THERMO = "36"
DEVICE_ELEVATOR = "44"
DEVICE_FAN = "48"

# Command Types
CMD_STATE = "00"
CMD_ON = "01"
CMD_OFF = "02"
CMD_QUERY = "3a"

# Packet Types
TYPE_SEND = "30b"
TYPE_ACK = "30d"

# Room Types
ROOM_LIVINGROOM = "00"
ROOM_BEDROOM = "01"
ROOM_ROOM1 = "02"
ROOM_ROOM2 = "03"
ROOM_ROOM3 = "04"
ROOM_ROOM4 = "05"
ROOM_ROOM5 = "06"
ROOM_ROOM6 = "07"
ROOM_ROOM7 = "08"
ROOM_ROOM8 = "09"

ROOM_NAMES = {
    "livingroom": ROOM_LIVINGROOM,
    "myhome": ROOM_LIVINGROOM,
    "bedroom": ROOM_BEDROOM,
    "room1": ROOM_ROOM1,
    "room2": ROOM_ROOM2,
    "room3": ROOM_ROOM3,
    "room4": ROOM_ROOM4,
    "room5": ROOM_ROOM5,
    "room6": ROOM_ROOM6,
    "room7": ROOM_ROOM7,
    "room8": ROOM_ROOM8,
}

# Sequence codes
SEQ_CODES = {"c": 1, "d": 2, "e": 3, "f": 4}

# Fan preset modes
FAN_PRESET_OFF = "Off"
FAN_PRESET_LOW = "Low"
FAN_PRESET_MEDIUM = "Medium"
FAN_PRESET_HIGH = "High"

FAN_PRESETS = [FAN_PRESET_OFF, FAN_PRESET_LOW, FAN_PRESET_MEDIUM, FAN_PRESET_HIGH]
