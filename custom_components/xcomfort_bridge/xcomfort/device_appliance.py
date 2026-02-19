"""Appliance device for xComfort integration."""

import logging

from .device_base import BridgeDevice
from .device_states import SwitchState

_LOGGER = logging.getLogger(__name__)


class Appliance(BridgeDevice):
    """Appliance/load device class."""

    def __init__(self, bridge, device_id, name, comp_id=None):
        """Initialize appliance device."""
        BridgeDevice.__init__(self, bridge, device_id, name, comp_id)

    def handle_state(self, payload):
        """Handle appliance state updates."""
        if "switch" not in payload:
            _LOGGER.debug("Appliance %s received non-switch payload, ignoring: %s", self.name, payload)
            return

        is_on = payload["switch"]
        _LOGGER.debug("Appliance %s state update: is_on=%s", self.name, is_on)
        self.state.on_next(SwitchState(is_on, payload))

    async def switch(self, switch: bool):
        """Switch appliance on/off."""
        _LOGGER.debug("Switching appliance %s: %s", self.name, "ON" if switch else "OFF")
        await self.bridge.switch_device(self.device_id, {"switch": switch})

    def __str__(self):
        """Return string representation of appliance device."""
        return f'Appliance({self.device_id}, "{self.name}", state:{self.state.value})'

    __repr__ = __str__
