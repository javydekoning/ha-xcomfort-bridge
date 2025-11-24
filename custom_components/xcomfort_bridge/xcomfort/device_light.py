"""Light device for xComfort integration."""

import logging

from .device_base import BridgeDevice
from .device_states import LightState

_LOGGER = logging.getLogger(__name__)


class Light(BridgeDevice):
    """Light device class."""

    def __init__(self, bridge, device_id, name, dimmable, comp_id=None):
        """Initialize light device."""
        BridgeDevice.__init__(self, bridge, device_id, name, comp_id)

        self.dimmable = dimmable

    def interpret_dimmvalue_from_payload(self, switch, payload):
        """Interpret dimmvalue from payload."""
        if not self.dimmable:
            return 99

        if not switch:
            return self.state.value.dimmvalue if self.state.value is not None else 99

        # Return dimmvalue if present, otherwise default to 99 (full brightness)
        return payload.get("dimmvalue", 99)

    def handle_state(self, payload):
        """Handle light state updates."""
        # Only process if this is a switch state update
        if "switch" not in payload:
            _LOGGER.debug("Light %s received non-switch payload, ignoring: %s", self.name, payload)
            return

        switch = payload["switch"]
        dimmvalue = self.interpret_dimmvalue_from_payload(switch, payload)
        _LOGGER.debug("Light %s state update: switch=%s, dimmvalue=%s", self.name, switch, dimmvalue)
        self.state.on_next(LightState(switch, dimmvalue, payload))

    async def switch(self, switch: bool):
        """Switch light on/off."""
        _LOGGER.debug("Switching light %s: %s", self.name, "ON" if switch else "OFF")
        await self.bridge.switch_device(self.device_id, {"switch": switch})

    async def dimm(self, value: int):
        """Set dimming value."""
        value = max(0, min(99, value))
        _LOGGER.debug("Setting light %s dim value to %s", self.name, value)
        await self.bridge.slide_device(self.device_id, {"dimmvalue": value})

    def __str__(self):
        """Return string representation of light device."""
        return f'Light({self.device_id}, "{self.name}", dimmable: {self.dimmable}, state:{self.state.value})'

    __repr__ = __str__


