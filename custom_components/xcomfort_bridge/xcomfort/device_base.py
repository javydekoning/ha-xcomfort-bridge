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

    def handle_state(self, payload):
        """Handle state updates."""
        self.state.on_next(DeviceState(payload))
