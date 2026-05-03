"""Heating valve device for xComfort integration."""

import logging

from .constants import DeviceStateUpdateText
from .device_base import BridgeDevice
from .device_states import HeatingValveState

_LOGGER = logging.getLogger(__name__)

# Sentinel value used by the bridge for "no reading"
_NO_READING = -100.0


class HeatingValve(BridgeDevice):
    """CHVZ-01/05 heating valve device class."""

    def __init__(self, bridge, device_id, name, comp_id):
        """Initialize heating valve device."""
        BridgeDevice.__init__(self, bridge, device_id, name)
        self.comp_id = comp_id

    def handle_state(self, payload):
        """Handle HeatingValve state updates."""
        _LOGGER.debug("HeatingValve %s: Received payload: %s", self.name, payload)

        ambient_temperature = None
        device_temperature = None
        valve_position = None
        power = None
        power_present = False
        has_update = False

        # Extract info array data
        if "info" in payload:
            for info in payload["info"]:
                text = info.get("text")
                value = info.get("value")
                if value is None:
                    continue
                if text == str(DeviceStateUpdateText.DEVICE_TEMPERATURE):
                    device_temperature = float(value)
                    has_update = True
                elif text == str(DeviceStateUpdateText.AMBIENT_TEMPERATURE):
                    ambient_temperature = float(value)
                    has_update = True
                elif text in (
                    str(DeviceStateUpdateText.VALVE_POSITION),
                    str(DeviceStateUpdateText.DIMM_VALUE),
                ):
                    valve_position = float(value)
                    has_update = True

        # Extract direct payload values
        if "dimmvalue" in payload:
            valve_position = float(payload["dimmvalue"])
            has_update = True

        if "power" in payload:
            power = float(payload["power"])
            power_present = True
            has_update = True

        # Keep last known values when partial updates arrive
        last_state = self.state.value
        if last_state is not None:
            if (
                ambient_temperature is None
                and last_state.ambient_temperature is not None
            ):
                ambient_temperature = last_state.ambient_temperature
            if device_temperature is None and last_state.device_temperature is not None:
                device_temperature = last_state.device_temperature
            if valve_position is None and last_state.valve_position is not None:
                valve_position = last_state.valve_position
            if not power_present and last_state.power is not None:
                power = last_state.power

        # Treat sentinel value -100.0 as None
        if ambient_temperature == _NO_READING:
            ambient_temperature = None
        if device_temperature == _NO_READING:
            device_temperature = None

        # curstate=0 means valve is idle — still emit a state update so HA reflects it
        if "curstate" in payload:
            has_update = True

        if has_update:
            _LOGGER.debug(
                "HeatingValve %s state update: ambient_temp=%s°C, device_temp=%s°C, valve=%s%%, power=%sW",
                self.name,
                ambient_temperature,
                device_temperature,
                valve_position,
                power,
            )
            self.state.on_next(
                HeatingValveState(
                    ambient_temperature,
                    device_temperature,
                    valve_position,
                    power,
                    payload,
                )
            )
