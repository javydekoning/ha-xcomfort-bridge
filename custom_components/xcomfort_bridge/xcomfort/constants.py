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
    """Climate state (op mode) enumeration.

    Corresponds to JS enum `ma` — the VARIOUS value appears when a room
    contains multiple actuators in different states.
    """

    Off = 0
    HeatingAuto = 1
    HeatingManual = 2
    CoolingAuto = 3
    CoolingManual = 4
    Various = 5


class Messages(IntEnum):
    """Message types for xComfort communication.

    The app splits these into two TypeScript enums (commands vs responses).
    They share a numeric namespace and are flattened here into one enum.
    """

    # --- Transport / errors (JS enum `xt`) ---
    NACK_INFO_UNKNOWN_DEVICE = -100
    NACK_INFO_DEVICE_NOT_DIMMABLE = -99
    NACK_INFO_INVALID_ACTION = -98
    IDLE = -1
    NACK = 0
    ACK = 1
    HEARTBEAT = 2

    # --- Connection / secure channel / auth ---
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

    # --- Diagnostic / test ---
    TEST_ON = 100
    TEST_OFF = 101
    TEST_CRYPTO = 102
    TEST_ALERT = 104
    TEST_DEVICE_STATE = 105
    TEST_COMMAND = 120

    # --- Bulk data requests / CRUD ---
    INITIAL_DATA = 240
    HOME_DATA = 242
    DIAGNOSTICS = 243
    SAVE_CONFIG = 244
    REQUEST_CONFIG_LIST = 245
    RESTORE_CONFIG = 246
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
    UPDATE_COMP = 275
    DELETE_COMP = 276
    ARRANGE_COMPS = 277
    FORCE_WRITE_COMP = 278
    ACTION_SLIDE_DEVICE = 280
    ACTION_SWITCH_DEVICE = 281
    ACTION_SLIDE_ROOM = 283
    ACTION_SWITCH_ROOM = 284
    ACTIVATE_SCENE = 285
    FOUND_COMP_RESPONSE = 286
    UPDATE_COMP_EDIT_STATE = 287
    SET_REMOTE_CONFIG = 288
    START_ACTUATOR_CONFIG = 289

    # --- Device / room / scene state (JS enum `Ao` — bridge responses) ---
    ADD_DEVICE = 290
    SET_DEVICE_STATE = 291
    SET_DEVICE_INFO = 292
    SET_ROOM_STATE = 293
    SET_ROOM_INFO = 294
    APP_INFO = 295
    DEVICE_DELETED = 296
    ROOM_DELETED = 297
    SCENE_DELETED = 298
    TIMER_DELETED = 299
    SET_ALL_DATA = 300
    SET_ROOM_ID = 301
    SET_SCENE_ID = 302
    SET_BRIDGE_DATA = 303
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
    CLIMATE_DELETED = 314

    # --- Smart scenes / time programs / push notes / users / locks ---
    SET_TIME_FORCE = 333
    SET_SMART_SCENE_AUTO_STATE = 334
    DELETE_TIME_PROGRAM = 335
    SET_TIME_PROGRAM = 336
    DELETE_SMART_CONDITION = 337
    SET_SMART_CONDITION = 338
    DELETE_PUSHNOTE = 339
    SET_PUSHNOTE = 340
    DELETE_CONFIG = 341
    DELETE_USER = 342
    SET_LOCK = 343
    SEND_TEST_NOTIFICATION = 344
    SET_USER = 345
    UPDATE_USER_CREDENTIALS = 346
    RESET_USER_CREDENTIALS = 347
    SET_NOTIFICATIONS = 348
    SET_INTEGRATION_STATE = 349

    # --- Climate / heating / shading / alarms / integrations / locks ---
    SET_CLIMATE_PROGRAM = 350
    DELETE_CLIMATE_PROGRAM = 351
    SET_ROOM_CLIMATE = 352
    SET_HEATING_STATE = 353
    SET_ROOM_SHADING_STATE = 354
    SET_DEVICE_SHADING_STATE = 355
    SET_DEVICE_ALARM_STATE = 356
    GET_INTEGRATION = 357
    UNLINK_INTEGRATION = 358
    OPERATE_LOCK = 359
    SET_CLIMATE_PROGRAM_ID = 360
    HEATING_PROGRAM_DELETED = 362
    SET_ROOM_CLIMATE_STATE = 363
    SET_BRIDGE_STATE = 364
    LOCK_DELETED = 365
    SET_LOCK_STATE = 366
    SET_USER_ID = 367
    SET_USER_CREDENTIALS_RESPONSE = 368
    USER_DELETED = 369
    DELETE_CONFIG_RESPONSE = 370
    SET_PUSHNOTE_ID = 371
    SET_SMART_CONDITION_ID = 372
    SET_TIME_PROGRAM_ID = 373
    SET_SCENE_STATE = 374
    PUSHNOTE_DELETED = 375
    SMART_CONDITION_DELETED = 376
    TIME_PROGRAM_DELETED = 377
    SET_CLIENT_RESPONSE = 378
    SET_CLIENT_INFO = 379
    SET_DEVICE_ACTUATOR_STATE = 380
    SET_CLIENT = 381
    CLIENT_BRIDGE_DELETED = 382
    DELETE_CLIENT_BRIDGE = 383
    ALLOCATE_BRIDGE_RESPONSIBILITY = 384
    SET_MASTER_CLIENT = 385

    # --- Energy management ---
    SET_ENERGY_DATA = 386
    SET_ENERGY_TARIFF = 387
    REQUEST_TARIFF_INFO = 388
    TARIFF_INFO = 389
    SET_ENERGY_MONITORING = 390
    SET_ENERGY_CONTROL = 391
    ENERGY_CONTROL_SET_MODE = 392
    SET_ENERGY_STATE = 393
    SET_ENERGY_MONITORING_VIEW = 394
    REQUEST_ENERGY_HISTORY = 395
    ENERGY_HISTORY = 396
    SET_ENERGY_METER = 397
    DELETE_ENERGY_METER = 398
    SET_ENERGY_METER_ID = 399
    ENERGY_METER_DELETED = 400
    SET_ENERGY_METER_STATE = 401

    # --- Bridge actions / auth-key rotation / audit ---
    TRIGGER_BRIDGE_ACTION = 402
    TRIGGER_BRIDGE_ACTION_RESPONSE = 403
    INIT_SET_AUTH_KEY = 404
    NEW_AUTH_KEY = 405
    CONFIRM_SET_AUTH_KEY = 406
    NEW_AUTH_KEY_CONFIRMED = 407
    AUDIT_LOGS = 408


class WebConnectMessages(IntEnum):
    """Cloud-relay protocol messages (JS enum `P`).

    Used when the app connects to a bridge indirectly through
    Eaton's web-connect service (xcomfortbridge.eaton.com). Not
    used by this integration — bridges here are always local.
    """

    WEB_CONNECT_WELCOME = 50
    WEB_CONNECT_IDENTIFY = 51
    WEB_CONNECT_ESTABLISHED = 54
    WEB_CONNECT_DECLINED = 55
    WEB_CONNECT_ONLINE_STATE = 600
    WEB_CONNECT_ONLINE_STATE_RESULT = 601
    WEB_CONNECT_DC_START = 602
    WEB_CONNECT_DC_ESTABLISHED = 603
    WEB_CONNECT_DC_DECLINED = 604
    WEB_CONNECT_DC_OUT = 612
    WEB_CONNECT_DC_IN = 613
    WEB_CONNECT_PLUGIN_MESSAGE_IN = 616
    WEB_CONNECT_PLUGIN_MESSAGE_OUT = 617
    WEB_CONNECT_PING = 618
    WEB_CONNECT_PONG = 619
    WEB_CONNECT_DC_CLOSED = 620


class ShadeOperationState(IntEnum):
    """Shade operation states (JS enum `hl`)."""

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


class ShadingState(IntEnum):
    """Shading runtime state (JS enum `Rd`)."""

    UNDEFINED = 0
    STOPPED = 1
    MOVING_UP = 2
    MOVING_DOWN = 3
    SAFETY_UP = 4
    SAFETY_DOWN = 5
    STOPPED_OVERTEMP = 6
    STOPPED_OVERLOAD = 7


class ShadingType(IntEnum):
    """Physical shading type (JS enum `gm`)."""

    ZIP_SCREEN = 1
    SHUTTER_BLINDS = 2
    AWNINGS = 3
    VERTICAL_BLINDS = 4
    ROLLER_BLINDS = 5
    PLEATED_BLINDS = 6


class DeviceTypes(IntEnum):
    """Device types reported in device payloads (devType field).

    These identify the functional role of a device within a component.
    A single component (e.g. a Pushbutton Multisensor) can expose multiple
    devices with different devTypes (e.g. SWITCH + TEMP_HUMIDITY_SENSOR).

    Values 201, 211, 220 appear in runtime payloads from rocker channels
    but are not named in the app's TS enum `un`; names are retained from
    the original Python implementation for readability.
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
    """Heating types for xComfort devices (JS enum `Bl`)."""

    UNDEFINED = 0
    ELECTRIC_FLOOR_FOIL = 1
    ELECTRIC_FLOOR_CABLE = 2
    WATER_FLOOR = 3
    ELECTRIC_RADIATOR = 4
    ELECTRIC_INFRARED = 5
    WATER_RADIATOR = 6
    OTHER = 7


class ComponentTypes(IntEnum):
    """Component types (compType field) — JS enum `Fn`.

    A component represents the physical hardware module. Each component
    exposes one or more devices (see DeviceTypes). Canonical names from
    the app are shown as comments where the Python name differs for
    readability.
    """

    VOID_COMP_TYPE = 0
    PUSH_BUTTON_1_CHANNEL = 1  # app: PUSHBUTTON_1FOLD
    PUSH_BUTTON_2_CHANNEL = 2  # app: PUSHBUTTON_2FOLD
    PUSH_BUTTON_4_CHANNEL = 3  # app: PUSHBUTTON_4FOLD
    BINARY_INPUT_230V = 19  # app: BINARY_INPUT_230
    BINARY_INPUT_BATTERY = 20  # app: BINARY_INPUT_BATT
    TEMPERATURE_SENSOR = 23  # app: TEMPERATURSENSOR
    SHADING_ACTUATOR_LEGACY = 27  # app: SHADING_ACTUATOR (older variant)
    MOTION_SENSOR = 29
    REMOTE_CONTROL_2_CHANNEL = 48  # app: REMOTE_CONTROL
    REMOTE_CONTROL_12_CHANNEL = 49  # app: REMOTE_CONTROL_12FOLD
    ROUTER_ACTUATOR = 52
    HEATING_VALVE = 65  # app: HEIZ_VENTIL
    MULTI_HEATING_ACTUATOR = 71  # app: MULTI_AKTOR_12FACH
    LIGHT_SWITCH_ACTUATOR = 74  # app: SWITCHING_ACTUATOR
    DOOR_WINDOW_SENSOR = 76  # app: WINDOW_SENSOR
    DIMMING_ACTUATOR = 77
    RC_TOUCH = 78  # app: RCF55
    HEATING_ACTUATOR_1_CHANNEL = 81  # app: HEIZAKT
    BRIDGE = 83
    WATER_GUARD = 84
    WATER_SENSOR = 85
    SHADING_ACTUATOR = 86  # app: SHADING_ACTUATOR_2021
    PUSH_BUTTON_MULTI_SENSOR_1_CHANNEL = 87  # app: PBMS_1FOLD
    PUSH_BUTTON_MULTI_SENSOR_2_CHANNEL = 88  # app: PBMS_2FOLD
    PUSH_BUTTON_MULTI_SENSOR_4_CHANNEL = 89  # app: PBMS_4FOLD
    WEATHER_STATION = 90


class DeviceUsage(IntEnum):
    """Usage classification for switching/dimming actuators (JS enum `Dn`).

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
    """State info categories used in SET_STATE_INFO payloads (JS enum `yo`).

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


class BinaryStateValue(IntEnum):
    """Discrete values for binary state payloads (JS enum `Nd`).

    Used inside state info items to encode the current binary condition
    (on/off, motion/no-motion, open/closed, etc.).
    """

    ON = 1
    OFF = 2
    SAFETY_ACTIVE = 3
    WATER_ON = 4
    WATER_OFF = 5
    ALARM_ON = 6
    ALARM_SILENT = 7
    MOTION = 8
    NO_MOTION = 9
    CLOSED = 10
    OPENED = 11
    RAIN = 12
    NO_RAIN = 13
    WATER = 14
    NO_WATER = 15
    ACTIVE = 16
    INACTIVE = 17
    SUN_IS_UP = 18
    SUN_IS_DOWN = 19


class WindoorsState(IntEnum):
    """Door/window sensor state (JS enum `dw`)."""

    UNKNOWN = 0
    OPEN = 1
    AJAR = 2
    CLOSED = 3


class LockState(IntEnum):
    """Lock state (JS enum `ad`)."""

    UNKNOWN = 0
    LOCKED = 1
    UNLOCKED = 2


class TempSensorRole(IntEnum):
    """Role of a temperature sensor in a climate zone (JS enum `_r`)."""

    NOT_USED = 0
    FLOOR_SENSOR = 1
    ROOM_SENSOR = 4
    OUTSIDE_SENSOR = 5


class EnergyMeterUsage(IntEnum):
    """Energy meter usage classification (JS enum `Mr`)."""

    AREA_TOTAL = 0
    COMBINED_APPLIANCE = 1
    EV_CHARGING = 2
    PV_METER = 3
    HEATPUMP = 4
    SPECIAL_APPLIANCE = 5
    WATER_HEATER = 6


class EnergyMeterType(IntEnum):
    """Energy meter hardware type (JS enum `D0`)."""

    VOID = 0
    EATON_EMD3P = 1
    HOMEWIZARD_P1 = 2


class EnergyDataType(IntEnum):
    """Energy data view types (JS enum `xu`)."""

    ELECTRICAL_ENERGY = 0
    ACTIVE_POWER = 1
    COSTS = 2
    CO2 = 3


class ConnectionRole(IntEnum):
    """Bridge connection role — master/client topology (JS enum `Pc`)."""

    VOID = 0
    MASTER = 1
    CLIENT = 2


class ConnectionState(IntEnum):
    """High-level socket state (JS enum `Oi`)."""

    CLOSED = 0
    CONNECTED = 1
    CONNECTING = 2
    RECONNECTING = 3
    DISCONNECTING = 4


class RemoteConnectionState(IntEnum):
    """Remote (cloud) connection state (JS enum `Ka`)."""

    DISABLED = 0
    ENABLED = 1
    MASTER = 2
    CLIENT = 3


class ConfigSection(IntEnum):
    """Configuration sections available in the bridge (JS enum `Ps`)."""

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
    """Device category — actuator vs sensor (JS enum `wc`)."""

    ROOM = 0
    ACTUATOR = 1
    SCENE = 2
    SENSOR = 3


class UserRole(IntEnum):
    """User role (JS enum `Go`)."""

    GUEST = 0
    USER = 1
    ADMIN = 2
    DEFAULT_ADMIN = 3
    THIRD_PARTY_INTEGRATION = 4


class BridgeAction(IntEnum):
    """Triggered bridge actions (JS enum `I0`)."""

    WRITE_TO_FLASH = 1
    DELETE_ENERGY_TARIFF = 2
    RESTART_BRIDGE = 3


class DimmingProfile(IntEnum):
    """Dimming profiles for dimming actuators (dp field).

    Controls the dimming curve used by the actuator. The i18n keys for
    these values are 1350, 1360, 1351, 1361-1376 in en.json.
    """

    UNKNOWN = 1350
    ON_OFF_ONLY = 1351
    USER_DEFINED = 1360
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


class DimmAction(IntEnum):
    """Commands sent in slide/switch device actions (JS enum `or`).

    Values 0-116 are dim-value set commands (0 = off / brightness, 100 = on,
    111-116 are timed/blinking variants). 140-148 lock one actuator's
    value; 1001/1002 lock everything.
    """

    BRIGHTNESS = 0
    OFF = 0
    ON = 100
    ON_DELAY = 111
    ON_OFF_DELAY = 112
    ON_OFF_DELAY_WARNING = 113
    PULSE = 114
    BLINKING = 116
    UNLOCK_ON = 140
    UNLOCK_OFF = 141
    UNLOCK_OLD_VALUE = 142
    LOCK_ON = 146
    LOCK_OFF = 147
    LOCK_OLD_VALUE = 148
    UNLOCK_ALL = 1001
    LOCK_ALL = 1002


class DeviceStateUpdateText(IntEnum):
    """Text IDs used in device info/state update payloads.

    These numeric codes appear as strings in the 'text' field of info items
    and correspond to i18n translation keys in the app's en.json.
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
    SIGNAL_QUALITY = 1111  # "Quality"
    NOT_CONFIGURED = 1112  # "Not yet configured"
    # Battery levels
    BATTERY_EMPTY = 1113
    BATTERY_WEAK = 1114
    BATTERY_MEDIUM = 1115
    BATTERY_GOOD = 1116
    BATTERY_FULL = 1117
    BATTERY_UNKNOWN = 1118
    MAINS_POWERED = 1119
    EXTERNAL_CONNECTIONS = 1120  # {{value}} connections
    PERCENTAGE = 1121  # {{value}}% (generic)
    # Water sensor status
    WATER_DETECTED = 1129
    WATER_OK = 1130
    WATER_SENSOR_UNKNOWN = 1131
    # Shading
    POSITION = 1132  # Position: {{value}}
    CALIBRATION_NEEDED = 1133
    OCCUPIED_RESENDER_SLOTS = 1134
    # Aggregate room states
    SOME_STATES_UNKNOWN = 1200
    ALL_STATES_UNKNOWN = 1201
    SOME_TROUBLED = 1202
    ALL_TROUBLED = 1203
    VALUE_UNKNOWN = 1220
    VALUE_ERROR = 1221
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
