"""Room module for xComfort integration."""

from enum import Enum
import logging

import rx

from .constants import Messages

_LOGGER = logging.getLogger(__name__)


class RctMode(Enum):
    """RCT mode enumeration."""

    Cool = 1
    Eco = 2
    Comfort = 3


class RctState(Enum):
    """RCT state enumeration."""

    Idle = 0
    Auto = 1
    Active = 2


class RctModeRange:
    """RCT mode range class."""

    def __init__(self, min_val: float, max_val: float):
        """Initialize RCT mode range."""
        self.Min = min_val
        self.Max = max_val


class RoomState:
    """Room state class."""

    def __init__(
        self,
        setpoint,
        temperature,
        humidity,
        power,
        mode: RctMode,
        state: RctState,
        raw,
    ):
        """Initialize room state."""
        self.setpoint = setpoint
        self.temperature = temperature
        self.humidity = humidity
        self.power = power
        self.mode = mode
        self.raw = raw
        self.rctstate = state

    def __str__(self):
        """Return string representation of room state."""
        return (
            f"RoomState({self.setpoint}, {self.temperature}, {self.humidity},{self.mode},{self.rctstate} {self.power})"
        )

    __repr__ = __str__


class Room:
    """Room class for xComfort integration."""

    def __init__(self, bridge, room_id, name: str):
        """Initialize room."""
        self.bridge = bridge
        self.room_id = room_id
        self.name = name
        self.state = rx.subject.BehaviorSubject(None)
        self.modesetpoints = {}

    def handle_state(self, payload):
        """Handle room state updates."""
        _LOGGER.debug("Room %s: Received payload: %s", self.name, payload)
        old_state = self.state.value

        if old_state is not None:
            old_state.raw.update(payload)
            payload = old_state.raw

        setpoint = payload.get("setpoint", None)
        temperature = payload.get("temp", None)
        humidity = payload.get("humidity", None)
        power = payload.get("power", 0.0)

        mode = None
        if "currentMode" in payload:  # When handling from _SET_ALL_DATA
            mode = RctMode(payload.get("currentMode", None))
        if "mode" in payload:  # When handling from _SET_STATE_INFO
            mode = RctMode(payload.get("mode", None))

        # When handling from _SET_ALL_DATA, we get the setpoints for each mode/preset
        # Store these for later use
        if "modes" in payload:
            for mode_data in payload["modes"]:
                self.modesetpoints[RctMode(mode_data["mode"])] = float(mode_data["value"])
            _LOGGER.debug("Room %s: Loaded mode setpoints: %s", self.name, self.modesetpoints)

        currentstate = None
        if "state" in payload:
            currentstate = RctState(payload.get("state", None))

        _LOGGER.debug(
            "Room %s state update: temp=%s°C, setpoint=%s°C, humidity=%s%%, mode=%s, state=%s, power=%s",
            self.name,
            temperature,
            setpoint,
            humidity,
            mode.name if mode else None,
            currentstate.name if currentstate else None,
            power,
        )

        self.state.on_next(RoomState(setpoint, temperature, humidity, power, mode, currentstate, payload))

    async def set_target_temperature(self, setpoint: float):
        """Set target temperature for room."""
        # Validate that new setpoint is within allowed ranges.
        # if above/below allowed values, set to the edge value
        setpointrange = self.bridge.rctsetpointallowedvalues[RctMode(self.state.value.mode)]

        original_setpoint = setpoint
        setpoint = min(setpoint, setpointrange.Max)
        setpoint = max(setpoint, setpointrange.Min)

        if original_setpoint != setpoint:
            _LOGGER.warning(
                "Room %s: Requested setpoint %s°C adjusted to %s°C (range: %s-%s°C)",
                self.name,
                original_setpoint,
                setpoint,
                setpointrange.Min,
                setpointrange.Max,
            )

        _LOGGER.debug(
            "Room %s: Setting target temperature to %s°C (mode: %s)", self.name, setpoint, self.state.value.mode.name
        )

        # Store new setpoint for current mode
        self.modesetpoints[self.state.value.mode.value] = setpoint

        await self.bridge.send_message(
            Messages.SET_HEATING_STATE,
            {
                "roomId": self.room_id,
                "mode": self.state.value.mode.value,
                "state": self.state.value.rctstate.value,
                "setpoint": setpoint,
                "confirmed": False,
            },
        )

    async def set_mode(self, mode: RctMode):
        """Set room mode."""
        # Find setpoint for the mode we are about to set, and use that
        # When transmitting heating_state message.
        newsetpoint = self.modesetpoints.get(mode)
        _LOGGER.debug("Room %s: Setting mode to %s (setpoint: %s°C)", self.name, mode.name, newsetpoint)

        await self.bridge.send_message(
            Messages.SET_HEATING_STATE,
            {
                "roomId": self.room_id,
                "mode": mode.value,
                "state": self.state.value.rctstate.value,
                "setpoint": newsetpoint,
                "confirmed": False,
            },
        )

    def __str__(self):
        """Return string representation of room."""
        return f'Room({self.room_id}, "{self.name}")'

    __repr__ = __str__
