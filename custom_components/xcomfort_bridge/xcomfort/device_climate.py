"""Climate devices for xComfort integration."""

import logging

import rx

from .constants import DeviceStateUpdateText
from .device_base import BridgeDevice
from .device_states import HeaterState, RcTouchState

_LOGGER = logging.getLogger(__name__)


class RcTouch(BridgeDevice):
    """RcTouch device class."""

    def __init__(self, bridge, device_id, name, comp_id):
        """Initialize RcTouch device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.comp_id = comp_id
        self.virtual_rocker_id = device_id + 1  # Virtual rocker always has device_id + 1

        # Separate observable for button events from the virtual rocker
        self.button_state = rx.subject.BehaviorSubject(None)
        self.virtual_rocker_payload = {}

    def handle_state(self, payload):
        """Handle RcTouch state updates."""
        _LOGGER.debug("RcTouch %s: Received payload: %s", self.name, payload)
        temperature = None
        humidity = None
        if "info" in payload:
            for info in payload["info"]:
                if info["text"] == str(DeviceStateUpdateText.AMBIENT_TEMPERATURE):
                    temperature = float(info["value"])
                if info["text"] == str(DeviceStateUpdateText.HUMIDITY):
                    humidity = float(info["value"])

        if temperature is not None and humidity is not None:
            _LOGGER.debug("RcTouch %s state update: temp=%s°C, humidity=%s%%", self.name, temperature, humidity)
            self.state.on_next(RcTouchState(temperature, humidity, payload))

    def handle_virtual_rocker_state(self, payload):
        """Handle button state updates from the virtual rocker."""
        self.virtual_rocker_payload.update(payload)

        if "curstate" in payload:
            button_state = bool(payload["curstate"])
            _LOGGER.debug("RcTouch %s button state update: %s", self.name, "PRESSED" if button_state else "RELEASED")
            self.button_state.on_next(button_state)


class Heater(BridgeDevice):
    """Heater device class."""

    def __init__(self, bridge, device_id, name, comp_id):
        """Initialize heater device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.comp_id = comp_id

    def handle_state(self, payload):
        """Handle Heater state updates."""
        _LOGGER.debug("Heater %s: Received payload: %s", self.name, payload)

        device_temperature = None
        heating_demand = None
        power = None

        # Extract info array data
        if "info" in payload:
            for info in payload["info"]:
                if info["text"] == str(DeviceStateUpdateText.DEVICE_TEMPERATURE):
                    device_temperature = float(info["value"])
                elif info["text"] == str(DeviceStateUpdateText.DIMM_VALUE):
                    heating_demand = float(info["value"])

        # Extract direct payload values
        if "dimmvalue" in payload:
            heating_demand = float(payload["dimmvalue"])

        if "power" in payload:
            power = float(payload["power"])

        # Only update state if we have at least one meaningful value
        if any(v is not None for v in [device_temperature, heating_demand, power]):
            _LOGGER.debug(
                "Heater %s state update: temp=%s°C, demand=%s%%, power=%sW",
                self.name,
                device_temperature,
                heating_demand,
                power,
            )
            self.state.on_next(HeaterState(device_temperature, heating_demand, power, payload))
