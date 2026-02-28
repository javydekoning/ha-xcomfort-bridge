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
        prev_state = self.state.value
        prev_power = getattr(prev_state, "power", None) if prev_state else None
        merged_raw = dict(prev_state.raw) if prev_state and prev_state.raw else {}
        merged_raw.update(payload)

        if "switch" not in payload and "power" not in payload and "dimmvalue" not in payload:
            _LOGGER.debug("Light %s received payload without switch/power/dimmvalue, ignoring: %s", self.name, payload)
            return

        switch = payload.get("switch", prev_state.switch if prev_state else False)
        dimmvalue = self.interpret_dimmvalue_from_payload(switch, payload)

        power = prev_power
        if "power" in payload:
            power = float(payload["power"])
        elif (not switch) or dimmvalue == 0:
            power = 0.0

        _LOGGER.debug("Light %s state update: switch=%s, dimmvalue=%s, power=%s", self.name, switch, dimmvalue, power)
        self.state.on_next(LightState(switch, dimmvalue, power, merged_raw))

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

