"""Binary sensor devices for xComfort integration."""

import logging

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
