"""Binary sensor devices for xComfort integration."""

import logging

import rx

from .constants import DeviceStateUpdateText
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


# Battery text IDs reported in the component "info" list, mapped to an
# approximate percentage. The bridge only reports coarse levels.
_BATTERY_TEXT_TO_PERCENT: dict[str, int | None] = {
    str(DeviceStateUpdateText.BATTERY_EMPTY.value): 0,
    str(DeviceStateUpdateText.BATTERY_WEAK.value): 25,
    str(DeviceStateUpdateText.BATTERY_MEDIUM.value): 50,
    str(DeviceStateUpdateText.BATTERY_GOOD.value): 75,
    str(DeviceStateUpdateText.BATTERY_FULL.value): 100,
    str(DeviceStateUpdateText.BATTERY_UNKNOWN.value): None,
}


class MotionSensor(BridgeDevice):
    """Motion sensor device (component type 29, device type 200).

    Motion is reported on the device channel, battery level on the
    component (``info`` list of the component payload).
    """

    def __init__(self, bridge, device_id, name, comp_id, payload):
        """Initialize motion sensor device."""
        BridgeDevice.__init__(self, bridge, device_id, name, comp_id)
        self.payload = payload
        self.motion: bool | None = None
        self.battery_level: int | None = None
        self.battery = rx.subject.BehaviorSubject(None)
        self._comp_subscribed = False

        if "curstate" in payload:
            self.motion = self._parse_curstate(payload["curstate"])
            self.state.on_next(self.motion)

        self.wire_up_component()

    @staticmethod
    def _parse_curstate(value) -> bool | None:
        try:
            return int(value) != 0
        except (TypeError, ValueError):
            return None

    def wire_up_component(self) -> None:
        """Subscribe to component updates (battery). Idempotent."""
        if self._comp_subscribed:
            return
        comp = self.bridge._comps.get(self.comp_id)  # noqa: SLF001
        if comp is None:
            return
        self._comp_subscribed = True
        self._handle_comp_payload(comp.payload)
        comp.state.subscribe(
            lambda comp_state: (
                comp_state is not None and self._handle_comp_payload(comp_state.raw)
            )
        )

    def _handle_comp_payload(self, payload: dict | None) -> None:
        if not payload:
            return
        for info in payload.get("info", []):
            text = str(info.get("text"))
            if text in _BATTERY_TEXT_TO_PERCENT:
                level = _BATTERY_TEXT_TO_PERCENT[text]
                if level != self.battery_level:
                    self.battery_level = level
                    self.battery.on_next(level)
                return

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
