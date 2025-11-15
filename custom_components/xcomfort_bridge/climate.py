"""Climate platform for xComfort integration with Home Assistant."""
import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub
from .xcomfort.bridge import RctMode, RctState, Room
from .xcomfort.connection import Messages
from .xcomfort.devices import RcTouch

SUPPORT_FLAGS = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the xComfort climate platform.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities

    """
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        devices = hub.devices
        rooms = hub.rooms

        _LOGGER.debug("Found %d xcomfort devices", len(list(devices)))

        # Filter for RcTouch devices (devType=450)
        rc_touch_devices = [device for device in devices if isinstance(device, RcTouch)]
        _LOGGER.debug("Found %d RcTouch devices", len(rc_touch_devices))

        # Create a mapping of room_id to room for easy lookup
        rooms_by_id = {room.room_id: room for room in rooms}

        rcts = []
        for device in rc_touch_devices:
            # Get the room associated with this RcTouch device from the payload
            if device.state.value is not None and hasattr(device.state.value, 'raw'):
                temp_room_id = device.state.value.raw.get('tempRoom')
                if temp_room_id is not None:
                    room = rooms_by_id.get(temp_room_id)
                    if room is not None:
                        _LOGGER.debug("Creating climate entity for RcTouch device '%s' with room '%s'",
                                    device.name, room.name)
                        rct = HASSXComfortRcTouch(hass, hub, room, device)
                        rcts.append(rct)
                    else:
                        _LOGGER.warning("RcTouch device '%s' references room %d which was not found",
                                      device.name, temp_room_id)
                else:
                    _LOGGER.debug("RcTouch device '%s' has no tempRoom in payload", device.name)
            else:
                _LOGGER.debug("RcTouch device '%s' has no state yet", device.name)

        _LOGGER.debug("Added %d rc touch units", len(rcts))
        async_add_entities(rcts)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class HASSXComfortRcTouch(ClimateEntity):
    """Representation of an xComfort RC Touch climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO]
    _attr_supported_features = SUPPORT_FLAGS

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, room: Room, device: RcTouch):
        """Initialize the climate device.

        Args:
            hass: Home Assistant instance
            hub: XComfort hub instance
            room: Room instance from xComfort
            device: RcTouch device instance

        """
        self.hass = hass
        self.hub = hub
        self._room = room
        self._device = device
        self._name = device.name
        self._state = None

        self.rctpreset = RctMode.Comfort
        self.rctstate = RctState.Idle
        self.temperature = 20.0
        self.humidity = 50.0
        self.currentsetpoint = 20.0

        self._unique_id = f"climate_{DOMAIN}_{hub.identifier}-{device.device_id}"

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""

        _LOGGER.debug("Added to hass %s", self._name)

        # Subscribe to room state for heating control (setpoint, mode, power)
        if self._room.state is None:
            _LOGGER.debug("Room state is null for %s", self._name)
        else:
            self._room.state.subscribe(lambda state: self._room_state_change(state))

        # Subscribe to device state for temperature and humidity
        if self._device.state is None:
            _LOGGER.debug("Device state is null for %s", self._name)
        else:
            self._device.state.subscribe(lambda state: self._device_state_change(state))

    def _room_state_change(self, state):
        """Handle room state changes for heating control.

        Args:
            state: New state from the room

        """
        self._state = state

        if self._state is not None:
            if "currentMode" in state.raw:
                self.rctpreset = RctMode(state.raw["currentMode"])
            if "mode" in state.raw:
                self.rctpreset = RctMode(state.raw["mode"])
            self.currentsetpoint = state.setpoint

            _LOGGER.debug("Room state changed %s : %s", self._name, state)

            self.schedule_update_ha_state()

    def _device_state_change(self, state):
        """Handle device state changes for temperature and humidity.

        Args:
            state: New state from the RcTouch device

        """
        if state is not None:
            self.temperature = state.temperature
            self.humidity = state.humidity

            _LOGGER.debug("Device state changed %s : temp=%s, humidity=%s",
                         self._name, state.temperature, state.humidity)

            self.schedule_update_ha_state()

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode.

        Args:
            preset_mode: The new preset mode to set

        """
        _LOGGER.debug("Set Preset mode %s", preset_mode)

        if preset_mode == "Cool":
            mode = RctMode.Cool
        if preset_mode == PRESET_ECO:
            mode = RctMode.Eco
        if preset_mode == PRESET_COMFORT:
            mode = RctMode.Comfort
        if self.rctpreset != mode:
            await self._room.set_mode(mode)
            self.rctpreset = mode
            self.schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature.

        Args:
            **kwargs: Keyword arguments containing the new temperature

        """
        _LOGGER.debug("Set temperature %s", kwargs)

        # TODO: Move everything below into Room class in xcomfort-python library.
        # Latest implementation in the base library is broken, so everything moved here
        # To facilitate easier debugging inside HA.
        # Also consider changing the `mode` object on RoomState class to be just a number,
        # at current it is an object(possibly due to erroneous parsing of the 300/310-messages)
        setpoint = kwargs["temperature"]
        setpointrange = self._room.bridge.rctsetpointallowedvalues[RctMode(self.rctpreset)]

        setpoint = min(setpointrange.Max, setpoint)

        setpoint = max(setpoint, setpointrange.Min)

        payload = {
            "roomId": self._room.room_id,
            "mode": self.rctpreset.value,
            "state": self._room.state.value.rctstate.value,
            "setpoint": setpoint,
            "confirmed": False,
        }
        await self._room.bridge.send_message(Messages.SET_HEATING_STATE, payload)
        self._room.modesetpoints[self.rctpreset] = setpoint
        self.currentsetpoint = setpoint
        # After moving everything to base library, ideally line below should be the entry point
        # into the library for setting target temperature.
        # await self._room.set_target_temperature(kwargs["temperature"])

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._name,
            "manufacturer": "Eaton",
            "model": "RC Touch",
            "via_device": (DOMAIN, self.hub.hub_id),
        }

    @property
    def name(self):
        """Return the display name of this climate entity."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        The xComfort integration pushes state updates, so polling is not needed.
        """
        return False

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.temperature

    @property
    def hvac_mode(self):
        """Return current HVAC mode."""
        return HVACMode.AUTO

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return int(self.humidity)

    @property
    def hvac_action(self):
        """Return the current running HVAC action."""
        if self._state.power > 0:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        if self._state is None:
            return 40.0
        return self._room.bridge.rctsetpointallowedvalues[self.rctpreset].Max

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        if self._state is None:
            return 5.0
        return self._room.bridge.rctsetpointallowedvalues[self.rctpreset].Min

    @property
    def target_temperature(self):
        """Returns the setpoint from RC touch, e.g. target_temperature."""
        return self.currentsetpoint

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return ["Cool", PRESET_ECO, PRESET_COMFORT]

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        if self.rctpreset == RctMode.Cool:
            return "Cool"
        if self.rctpreset == RctMode.Eco:
            return PRESET_ECO
        if self.rctpreset == RctMode.Comfort:
            return PRESET_COMFORT
        _LOGGER.warning("Unexpected preset mode: %s", self.rctpreset)
        return None
