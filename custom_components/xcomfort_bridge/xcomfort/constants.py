"""Constants module for xComfort integration.

Enum values sourced from decompiled xComfort Bridge app v2.4.1.
"""

from enum import Enum, IntEnum


class ClimateMode(Enum):
    """Climate mode enumeration."""

    Unknown = 0
    FrostProtection = 1
    Eco = 2
    Comfort = 3


class ClimateState(Enum):
    """Climate state enumeration."""

    Off = 0
    HeatingAuto = 1
    HeatingManual = 2
    CoolingAuto = 3
    CoolingManual = 4


class Messages(IntEnum):
    """Message types for xComfort communication."""

    NACK = 0
    ACK = 1
    HEARTBEAT = 2
    CONNECTION_START = 10
    CONNECTION_CONFIRM = 11
    CONNECTION_ESTABLISHED = 12
    CONNECTION_DECLINED = 13
    SC_INIT = 14
    SC_PUBKEY = 15
    SC_SECRET = 16
    SC_ESTABLISHED = 17
    SC_INVALID = 18
    AUTH_LOGIN = 30
    AUTH_LOGIN_DENIED = 31
    AUTH_LOGIN_SUCCESS = 32
    AUTH_APPLY_TOKEN = 33
    AUTH_APPLY_TOKEN_RESPONSE = 34
    AUTH_VERIFY_TOKEN = 35
    AUTH_VERIFY_TOKEN_RESPONSE = 36
    AUTH_RENEW_TOKEN = 37
    AUTH_RENEW_TOKEN_RESPONSE = 38
    AUTH_KILL_TOKEN = 39
    TEST_ON = 100
    TEST_OFF = 101
    TEST_CRYPTO = 102
    TEST_ALERT = 104
    TEST_DEVICE_STATE = 105
    TEST_COMMAND = 120
    INITIAL_DATA = 240
    HOME_DATA = 242
    DIAGNOSTICS = 243
    INIT_SWUPDATE = 247
    DATA_SWUPDATE = 248
    START_SWUPDATE = 249
    UPDATE_BRIDGE = 250
    START_LEARNMODE = 251
    STOP_LEARNMODE = 252
    BARCODE_DEVICE = 253
    UPDATE_DEVICE = 254
    DELETE_DEVICE = 255
    ARRANGE_DEVICES = 256
    SET_ROOM = 257
    DELETE_ROOM = 259
    ARRANGE_ROOMS = 260
    SET_SCENE = 261
    DELETE_SCENE = 263
    ARRANGE_SCENES = 264
    EDIT_RF_PWD = 270
    SET_TIME = 271
    SET_ASTRO = 272
    SET_TIMER = 273
    DELETE_TIMER = 274
    ACTION_SLIDE_DEVICE = 280
    ACTION_SWITCH_DEVICE = 281
    ACTION_SLIDE_ROOM = 283
    ACTION_SWITCH_ROOM = 284
    ACTIVATE_SCENE = 285
    ADD_DEVICE = 290
    SET_DEVICE_STATE = 291
    SET_DEVICE_INFO = 292
    SET_ROOM_STATE = 293
    SET_ROOM_INFO = 294
    APP_INFO = 295
    DEVICE_DELETED = 296
    ROOM_DELETED = 297
    SCENE_DELETED = 298
    SET_ALL_DATA = 300
    SET_ROOM_ID = 301
    SET_SCENE_ID = 302
    SET_HOME_DATA = 303
    SET_DIAGNOSTICS = 304
    SET_TIMER_ID = 305
    FOUND_COMP = 306
    ADD_COMP = 307
    SET_COMP_INFO = 308
    COMP_DELETED = 309
    SET_STATE_INFO = 310
    CONFIG_SAVED = 311
    CONFIG_LIST = 312
    RESTORE_CONFIG_RESPONSE = 313
    SET_HEATING_PROGRAM = 350
    DELETE_HEATING_PROGRAM = 351
    SET_ROOM_HEATING = 352
    SET_HEATING_STATE = 353
    SET_ROOM_SHADING_STATE = 354
    SET_DEVICE_SHADING_STATE = 355
    SET_DEVICE_ALARM_STATE = 356
    GET_INTEGRATION = 357
    UNLINK_INTEGRATION = 358
    SET_HEATING_PROGRAM_ID = 360
    HEATING_PROGRAM_DELETED = 362
    SET_ROOM_HEATING_STATE = 363
    SET_BRIDGE_STATE = 364
    PUBLISH_MAIN_ELECTRICAL_ENERGY_USAGE = 401
    IDLE = -1
    NACK_INFO_INVALID_ACTION = -98
    NACK_INFO_DEVICE_NOT_DIMMABLE = -99
    NACK_INFO_UNKNOWN_DEVICE = -100


class ShadeOperationState(IntEnum):
    """Shade operation states."""

    OPEN = 0
    CLOSE = 1
    STOP = 2
    STEP_DOWN = 3
    STEP_UP = 4
    GO_TO = 5
    CALIBRATION = 10
    LOCK = 11
    UNLOCK = 12
    QUIT = 13


class DeviceTypes(IntEnum):
    """Device types reported in device payloads (devType field).

    These identify the functional role of a device within a component.
    A single component (e.g. a Pushbutton Multisensor) can expose multiple
    devices with different devTypes (e.g. SWITCH + TEMP_HUMIDITY_SENSOR).
    """

    ACTUATOR_SWITCH = 100
    ACTUATOR_DIMM = 101
    SHADING_ACTUATOR = 102
    # Sensor/input device types
    MOTION_SENSOR = 200  # Push switch channel on sensors
    ROCKER_SENSOR = 201  # Rocker channel on sensor components
    SWITCH = 202  # Switch channel (door/window sensors, pushbuttons)
    ROCKER_BINARY_INPUT = 211  # Rocker on binary input devices (230V / battery)
    ROCKER = 220  # Rocker channel on actuators & remotes
    # Temperature & climate
    TEMP_SENSOR = 410
    ACTUATOR_HEATING = 440
    HEATING_VALVE = 441
    ACTUATOR_MULTI_HEATING = 442  # Multi-zone heating actuator (e.g. CHAZ-01/12)
    RC_TOUCH = 450
    TEMP_HUMIDITY_SENSOR = 451
    ACTUATOR_ROUTER = 460
    # Water safety
    WATER_GUARD = 497
    WATER_SENSOR = 499
    # Weather
    WEATHER_STATION = 510


class HeatingTypes(IntEnum):
    """Heating types for xComfort devices."""

    ELECTRIC_FLOOR_FOIL = 1
    ELECTRIC_FLOOR_CABLE = 2
    WATER_FLOOR = 3
    ELECTRIC_RADIATOR = 4
    ELECTRIC_INFRARED = 5
    WATER_RADIATOR = 6


class ComponentTypes(IntEnum):
    """Component types (compType field).

    A component represents the physical hardware module. Each component
    exposes one or more devices (see DeviceTypes).
    """

    VOID_COMP_TYPE = 0
    PUSH_BUTTON_1_CHANNEL = 1
    PUSH_BUTTON_2_CHANNEL = 2
    PUSH_BUTTON_4_CHANNEL = 3
    BINARY_INPUT_230V = 19
    BINARY_INPUT_BATTERY = 20
    TEMPERATURE_SENSOR = 23
    SHADING_ACTUATOR_LEGACY = 27  # Older shading actuator
    MOTION_SENSOR = 29
    REMOTE_CONTROL_2_CHANNEL = 48
    REMOTE_CONTROL_12_CHANNEL = 49
    ROUTER_ACTUATOR = 52
    HEATING_VALVE = 65
    MULTI_HEATING_ACTUATOR = 71
    LIGHT_SWITCH_ACTUATOR = 74
    DOOR_WINDOW_SENSOR = 76
    DIMMING_ACTUATOR = 77
    RC_TOUCH = 78
    HEATING_ACTUATOR_1_CHANNEL = 81
    BRIDGE = 83
    WATER_GUARD = 84
    WATER_SENSOR = 85
    SHADING_ACTUATOR = 86  # 2021+ shading actuator
    PUSH_BUTTON_MULTI_SENSOR_1_CHANNEL = 87
    PUSH_BUTTON_MULTI_SENSOR_2_CHANNEL = 88
    PUSH_BUTTON_MULTI_SENSOR_4_CHANNEL = 89
    WEATHER_STATION = 90
    # Virtual component types (not physical hardware)
    SCENE = 1000
    HEATMODE = 1001
    BINARY_SENSOR = 1002


class DeviceUsage(IntEnum):
    """Usage classification for switching/dimming actuators.

    Determines how a device is categorized in the app UI and which
    HA platform should handle it.
    """

    LIGHT = 0
    LOAD = 1
    SUM_HEATING = 2
    SHADING = 3
    WATER = 4
    ROUTING = 5
    WATER_HEATING = 6
    VEHICLE_CHARGER = 7
    HIGH_LOAD_APPLIANCE = 8
    SUM_COOLING = 21
    SUM_HEATING_COOLING = 22
    HEATING = 23
    COOLING = 24
    HEATING_COOLING = 25
    SWITCH_HEATING_COOLING = 26
    SWITCH_COOLING = 27
    SWITCH_HEATING = 28
    BIN_NORMAL = 100
    BIN_HK_1_CONTACT = 101
    BIN_HK_2_CONTACTS = 102


class InfoType(IntEnum):
    """State info categories used in SET_STATE_INFO payloads.

    Each device state update carries a type field indicating what kind
    of sensor data or state change it represents.
    """

    LIGHTING_STATE = 1
    APPLIANCE_STATE = 2
    SHADING_STATE = 3
    WATER_GUARD_STATE = 4
    MOTION_SENSOR_STATE = 5
    WINDOORS_STATE = 6
    TEMPERATURE = 7
    HUMIDITY = 8
    BRIGHTNESS = 9
    WIND_SPEED = 10
    RAIN = 11
    WATER_SENSOR_STATE = 12
    TIME_PROGRAM = 13
    POWER = 14
    ENERGY_TARIFF = 15
    BINARY_STATE = 16
    SUN_STATE = 17


class TempSensorRole(IntEnum):
    """Role of a temperature sensor in a climate zone."""

    NOT_USED = 0
    FLOOR_SENSOR = 1
    ROOM_SENSOR = 4
    OUTSIDE_SENSOR = 5


class EnergyMeterUsage(IntEnum):
    """Energy meter usage classification."""

    AREA_TOTAL = 0
    COMBINED_APPLIANCE = 1
    EV_CHARGING = 2
    PV_METER = 3
    HEATPUMP = 4
    SPECIAL_APPLIANCE = 5
    WATER_HEATER = 6


class ConnectionRole(IntEnum):
    """Bridge connection role (master/client topology)."""

    VOID = 0
    MASTER = 1
    CLIENT = 2


class RemoteConnectionState(IntEnum):
    """Remote connection state for cloud connectivity."""

    DISABLED = 0
    ENABLED = 1
    MASTER = 2
    CLIENT = 3


class ConfigSection(IntEnum):
    """Configuration sections available in the bridge."""

    ROOMS = 1
    ACTUATORS_SENSORS = 2
    TIMERS = 3
    CLIMATE_FUNCTION = 4
    SHADING_CONTROL = 5
    LIGHTING_CONTROL = 6
    THIRD_PARTY = 7
    LEAKAGE_STOP = 8
    USER_MANAGEMENT = 9
    SCENES = 10
    BACKUP_RESTORE = 11
    REMOTE_CONNECTION_NOTIFICATIONS = 12
    GENERAL_INFO = 13
    MASTER_CLIENT = 14
    ENERGY_MGMT = 15
    INSTALLATION = 16


class DeviceCategory(IntEnum):
    """Device category (actuator vs sensor)."""

    ACTUATOR = 0
    SENSOR = 1


class DimmingProfile(IntEnum):
    """Dimming profiles for dimming actuators (dp field).

    Controls the dimming curve used by the actuator.
    """

    ON_OFF_ONLY = 1351
    RLC_STANDARD = 1361
    LED_1 = 1362
    LED_2 = 1363
    LED_3 = 1364
    CFL_ESL = 1365
    LED_4 = 1366
    LED_5 = 1367
    LED_6 = 1368
    LED_7 = 1369
    LINEAR_0_10V = 1370
    LINEAR_1_10V = 1371
    LOG_0_10V = 1372
    LOG_1_10V = 1373
    LED_LOW = 1374
    LED_MID = 1375
    LED_HIGH = 1376


class ComponentMode(IntEnum):
    """Operating modes for components (mode field).

    Different component types use different subsets of modes.
    Binary inputs (19/20): 1302-1305
    Switching actuators (74): 1306-1307
    Door/window sensors (76): 1308-1311
    """

    # Binary input / dimming actuator modes
    MODE_PUSHBUTTON = 1302
    MODE_SWITCH = 1303
    MODE_PUSHBUTTON_SWITCH = 1304
    MODE_ROCKER = 1305
    # Switching actuator modes
    SA_MODE_PUSHBUTTON = 1306
    SA_MODE_SWITCH = 1307
    # Door/window sensor modes
    WINDOW_ON_CLOSED = 1308
    WINDOW_ON_OPENED = 1309
    DOOR_ON_CLOSED = 1310
    DOOR_ON_OPENED = 1311


class DeviceStateUpdateText(IntEnum):
    """Text IDs used in device info/state update payloads.

    These numeric codes appear in the 'text' field of info items
    and correspond to i18n translation keys.
    """

    # Error / status
    SENSOR_OVERFLOW = 1100
    STATE_UNKNOWN = 1101
    TROUBLED = 1102
    LOCKED = 1103
    BLINKING = 1104
    OVERTEMPERATURE = 1105
    OVERLOAD = 1106
    LOAD_ERROR = 1107
    SIGNAL_STRENGTH = 1108  # -{{value}}dBm
    DEVICE_TEMPERATURE = 1109  # {{value}}°C
    POWER = 1110  # {{value}}W
    SIGNAL_QUALITY = 1111
    NOT_CONFIGURED = 1112
    # Battery levels
    BATTERY_EMPTY = 1113
    BATTERY_WEAK = 1114
    BATTERY_MEDIUM = 1115
    BATTERY_GOOD = 1116
    BATTERY_FULL = 1117
    BATTERY_UNKNOWN = 1118
    MAINS_POWERED = 1119
    EXTERNAL_CONNECTIONS = 1120  # {{value}} connections
    # Sensor values
    PERCENTAGE = 1121  # {{value}}% (valve, etc.)
    # Ambient sensors
    AMBIENT_TEMPERATURE = 1222  # {{value}}°C
    HUMIDITY = 1223  # {{value}}%
    PT1000_TEMPERATURE = 1224  # PT1000: {{value}}°C
    VALVE_POSITION = 1225  # Valve: {{value}}% (also used as heating demand)
    DIMM_VALUE = VALVE_POSITION  # Backward-compat alias
    POWER_ALT = 1226  # {{value}}W (alternative)
    SUM_REQUEST = 1227
    NOT_CONFIGURED_ALT = 1228
    # Weather station
    WIND_SPEED = 1240  # {{value}}m/s
    RAIN = 1241  # Rain
    NO_RAIN = 1242  # No Rain
    BRIGHTNESS = 1243  # {{value}} (lux)
    # Shading
    POSITION = 1132  # Position: {{value}}
    CALIBRATION_NEEDED = 1133
    # Motion
    MOTION = 1125
    NO_MOTION = 1126
