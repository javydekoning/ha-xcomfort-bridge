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
        prev_state = self.state.value
        prev_power = getattr(prev_state, "power", None) if prev_state else None
        merged_raw = dict(prev_state.raw) if prev_state and prev_state.raw else {}
        merged_raw.update(payload)

        if "switch" not in payload and "power" not in payload:
            _LOGGER.debug("Appliance %s received payload without switch/power, ignoring: %s", self.name, payload)
            return

        is_on = payload.get("switch", prev_state.is_on if prev_state else False)
        power = prev_power

        if "power" in payload:
            power = float(payload["power"])
        elif not is_on:
            power = 0.0

        _LOGGER.debug("Appliance %s state update: is_on=%s, power=%s", self.name, is_on, power)
        self.state.on_next(SwitchState(is_on, power, merged_raw))

    async def switch(self, switch: bool):
        """Switch appliance on/off."""
        _LOGGER.debug("Switching appliance %s: %s", self.name, "ON" if switch else "OFF")
        await self.bridge.switch_device(self.device_id, {"switch": switch})

    def __str__(self):
        """Return string representation of appliance device."""
        return f'Appliance({self.device_id}, "{self.name}", state:{self.state.value})'

    __repr__ = __str__
