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
            _LOGGER.debug("Door/Window sensor %s state update: %s", self.name, "CLOSED" if self.is_closed else "OPEN")

        self.state.on_next(self.is_closed)


class WindowSensor(DoorWindowSensor):
    """Window sensor device class."""


class DoorSensor(DoorWindowSensor):
    """Door sensor device class."""



