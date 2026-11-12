"""Base device class for xComfort integration."""

import rx

from .device_states import DeviceState


class BridgeDevice:
    """Base bridge device class."""

    def __init__(self, bridge, device_id, name, comp_id=None):
        """Initialize bridge device."""
        self.bridge = bridge
        self.device_id = device_id
        self.name = name
        self.comp_id = comp_id

        self.state = rx.subject.BehaviorSubject(None)
        # Last-known device temperature in °C, if reported via the payload's
        # info[] array (text code 1109). Populated centrally by the bridge
        # in _handle_device_payload; cached so partial state updates that
        # omit info[] don't blank the sensor reading.
        self._device_temperature_c: float | None = None

    def handle_state(self, payload):
        """Handle state updates."""
        self.state.on_next(DeviceState(payload))

    @property
    def device_temperature_c(self) -> float | None:
        """Return the device's internal hardware temperature in °C, if known.

        Reported by some actuators (switching/dimming/heating) for overload
        protection monitoring. See Bridge._handle_device_payload for how the
        value is extracted.
        """
        return self._device_temperature_c
