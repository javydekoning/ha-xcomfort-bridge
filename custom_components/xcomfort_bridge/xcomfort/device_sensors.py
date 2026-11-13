"""Binary sensor devices for xComfort integration."""

import logging

from .constants import DeviceStateUpdateText
from .device_base import BridgeDevice

_LOGGER = logging.getLogger(__name__)


class DoorWindowSensor(BridgeDevice):
    """Door/window sensor device class."""

    def __init__(self, bridge, device_id, name, comp_id, payload):
        """Initialize door/window sensor device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.comp_id = comp_id
        self.payload = payload
        self.is_open: bool | None = None
        self.is_closed: bool | None = None

    def handle_state(self, payload):
        """Handle door/window sensor state updates."""
        if (state := payload.get("curstate")) is not None:
            self.is_closed = state == 1
            self.is_open = not self.is_closed
            _LOGGER.debug(
                "Door/Window sensor %s state update: %s",
                self.name,
                "CLOSED" if self.is_closed else "OPEN",
            )

        self.state.on_next(self.is_closed)


class WindowSensor(DoorWindowSensor):
    """Window sensor device class."""


class DoorSensor(DoorWindowSensor):
    """Door sensor device class."""


class MotionSensor(BridgeDevice):
    """Motion sensor device (component type 29, device type 200).

    Motion is reported on the device channel. Battery and signal live on
    the component and are exposed by the generic diagnostic sensors.
    """

    def __init__(self, bridge, device_id, name, comp_id, payload):
        """Initialize motion sensor device."""
        BridgeDevice.__init__(self, bridge, device_id, name, comp_id)
        self.payload = payload
        self.motion: bool | None = None

        if "curstate" in payload:
            self.motion = self._parse_curstate(payload["curstate"])
            self.state.on_next(self.motion)

    @staticmethod
    def _parse_curstate(value) -> bool | None:
        try:
            return int(value) != 0
        except (TypeError, ValueError):
            return None

    def handle_state(self, payload):
        """Handle motion sensor state updates."""
        motion = self.motion
        if "curstate" in payload:
            motion = self._parse_curstate(payload["curstate"])
        else:
            _LOGGER.debug(
                "Motion sensor %s: state update without curstate: %s",
                self.name,
                payload,
            )

        _LOGGER.debug(
            "Motion sensor %s state update: %s (payload: %s)",
            self.name,
            "MOTION" if motion else "NO MOTION",
            payload,
        )
        self.motion = motion
        self.state.on_next(motion)


# Info text codes that report the water state; their `value` is the time of
# the last state change as "DD.MM.YYYY HH:MM" (bridge local time).
_WATER_STATE_INFO_CODES = {
    str(DeviceStateUpdateText.WATER_DETECTED),
    str(DeviceStateUpdateText.WATER_OK),
    str(DeviceStateUpdateText.WATER_SENSOR_UNKNOWN),
}


class WaterSensor(BridgeDevice):
    """Water sensor channel (component type 85, device type 499).

    Hardware: CWGA-0D/01. The wet/dry state is reported on the device
    channel via `curstate`: 0 = dry, 1 = water detected, anything else
    (2 after a bridge restart) = unknown. Battery and signal live on the
    component and are exposed by the generic diagnostic sensors.
    """

    def __init__(self, bridge, device_id, name, comp_id, payload):
        """Initialize water sensor device."""
        BridgeDevice.__init__(self, bridge, device_id, name, comp_id)
        self.payload = payload
        self.water_detected: bool | None = None
        self.last_changed: str | None = None

    @staticmethod
    def _parse_curstate(value) -> bool | None:
        try:
            state = int(value)
        except (TypeError, ValueError):
            return None
        if state == 0:
            return False
        if state == 1:
            return True
        return None

    def handle_state(self, payload):
        """Handle water sensor state updates."""
        if "curstate" in payload:
            self.water_detected = self._parse_curstate(payload["curstate"])

        for item in payload.get("info") or []:
            if str(item.get("text")) in _WATER_STATE_INFO_CODES and item.get("value"):
                self.last_changed = item["value"]

        _LOGGER.debug(
            "Water sensor %s state update: %s (payload: %s)",
            self.name,
            {True: "WATER", False: "DRY", None: "UNKNOWN"}[self.water_detected],
            payload,
        )
        self.state.on_next(self.water_detected)
