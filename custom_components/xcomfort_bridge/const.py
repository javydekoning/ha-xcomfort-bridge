"""Constants for the Eaton xComfort Bridge integration."""

DOMAIN = "xcomfort_bridge"
BUTTON_EVENT = f"{DOMAIN}_button_event"
CONF_MAC = "mac_address"
CONF_AUTH_KEY = "auth_key"
CONF_IDENTIFIER = "identifier"
CONF_DIMMING = "dimming"
CONF_GATEWAYS = "gateways"
CONF_POWER_ENERGY_SECTION = "power_energy_sensors"
CONF_ADD_ROOM_POWER_SENSORS = "add_room_power_sensors"
CONF_ADD_HEATER_POWER_SENSORS = "add_heater_power_sensors"
CONF_ADD_LIGHT_POWER_SENSORS = "add_light_power_sensors"
CONF_ADD_APPLIANCE_POWER_SENSORS = "add_appliance_power_sensors"

# Authentication mode selection. The bridge supports two equivalent login
# flavours over the same AUTH_LOGIN (msg 30) message — only the `username`
# field and the secret-entry UX differ:
#   - DEVICE: the one-time auth code shown in the app; username is "default".
#   - USER: a named user account configured in the app.
CONF_AUTH_MODE = "auth_mode"
CONF_USERNAME = "username"
AUTH_MODE_DEVICE = "device"
AUTH_MODE_USER = "user"
DEFAULT_DEVICE_USERNAME = "default"
