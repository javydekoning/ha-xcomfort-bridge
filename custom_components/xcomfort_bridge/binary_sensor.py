"""Binary sensor platform for xComfort integration with Home Assistant."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device_info import get_motion_sensor_device_info, get_water_sensor_device_info
from .entity_lifecycle import (
    init_entity_lifecycle,
    mark_entity_added,
    schedule_state_update_safely,
    subscribe_observable,
)
from .hub import XComfortHub
from .xcomfort.comp import Comp
from .xcomfort.constants import ComponentMode, ComponentTypes, DeviceUsage
from .xcomfort.devices import (
    DoorSensor,
    MotionSensor,
    Rocker,
    WaterSensor,
    WindowSensor,
)

_LOGGER = logging.getLogger(__name__)

_BINARY_INPUT_MODELS = {
    ComponentTypes.BINARY_INPUT_230V: "Binary Input 230V",
    ComponentTypes.BINARY_INPUT_BATTERY: "Binary Input Battery",
}
_BINARY_INPUT_MODE_NAMES = {
    ComponentMode.MODE_PUSHBUTTON: "pushbutton",
    ComponentMode.MODE_SWITCH: "switch",
    ComponentMode.MODE_PUSHBUTTON_SWITCH: "pushbutton_switch",
    ComponentMode.MODE_ROCKER: "rocker",
}


def _binary_input_mode(comp: Comp) -> ComponentMode | None:
    """Return the binary input component's configured mode, if known."""
    try:
        return ComponentMode(int(comp.payload.get("mode")))
    except (TypeError, ValueError):
        return None


def _binary_input_sensors(hub: XComfortHub) -> list["XComfortBinaryInputSensor"]:
    """Create contact-state sensors for binary input channels (CBEU / CAEU).

    Mirrors the xComfort app, which only treats a binary input channel as a
    binary state when its component is in Switch mode (1303) and the channel
    is a normal input (usage BIN_NORMAL or unset). Pushbutton modes (1302,
    1304) report curstate too but the app does not interpret it as a state,
    so those sensors are created disabled by default. Rocker mode (1305) and
    heating/cooling changeover contacts get no sensor.
    """
    sensors = []
    for device in hub.devices:
        if not isinstance(device, Rocker):
            continue
        comp = hub.bridge.comps.get(device.comp_id)
        if comp is None or comp.comp_type not in _BINARY_INPUT_MODELS:
            continue
        usage = device.payload.get("usage")
        if usage is not None and usage != DeviceUsage.BIN_NORMAL:
            _LOGGER.debug(
                "Binary input %s has usage %s (heating/cooling contact), skipping",
                device.name,
                usage,
            )
            continue
        mode = _binary_input_mode(comp)
        if mode == ComponentMode.MODE_SWITCH:
            enabled_default = True
        elif mode in (
            ComponentMode.MODE_PUSHBUTTON,
            ComponentMode.MODE_PUSHBUTTON_SWITCH,
        ):
            enabled_default = False
        else:
            _LOGGER.debug(
                "Binary input %s on %s has mode %s, no contact sensor",
                device.name,
                comp.name,
                comp.payload.get("mode"),
            )
            continue
        sensors.append(
            XComfortBinaryInputSensor(hub, device, comp, mode, enabled_default)
        )
    return sensors


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up xComfort binary sensors from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities

    """
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        """Wait for hub to complete initial load then set up binary sensors."""
        await hub.has_done_initial_load.wait()

        sensors = [
            XComfortDoorWindowSensor(hub, device)
            for device in hub.get_door_window_sensors()
        ]
        sensors.extend(
            XComfortMotionSensor(hub, device)
            for device in hub.devices
            if isinstance(device, MotionSensor)
        )
        sensors.extend(
            XComfortWaterSensor(hub, device)
            for device in hub.devices
            if isinstance(device, WaterSensor)
        )
        sensors.extend(_binary_input_sensors(hub))
        async_add_entities(sensors)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class XComfortDoorWindowSensor(BinarySensorEntity):
    """Representation of an xComfort door/window binary sensor."""

    def __init__(self, hub: XComfortHub, device: WindowSensor | DoorSensor) -> None:
        """Initialize the binary sensor.

        Args:
            hub: The xComfort hub instance
            device: The door or window sensor device

        """
        super().__init__()
        self._attr_name = device.name

        self.hub = hub
        self._device = device
        self._attr_state = device.is_open

        if isinstance(device, WindowSensor):
            self._attr_device_class = BinarySensorDeviceClass.WINDOW
        elif isinstance(device, DoorSensor):
            self._attr_device_class = BinarySensorDeviceClass.DOOR
        init_entity_lifecycle(self)

    async def async_added_to_hass(self):
        """Run when entity is added to Home Assistant.

        Sets up state change subscription if device state exists.

        """
        await super().async_added_to_hass()
        mark_entity_added(self)
        subscribe_observable(
            self, self._device.state, self._state_change, "device.state"
        )

    def _state_change(self, state: bool):
        """Handle state changes from the device.

        Args:
            state: New state value (True for open, False for closed)

        """
        self._attr_state = state
        schedule_state_update_safely(self, "device.state")

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on.

        Returns:
            True if the sensor detects the door/window is open, False if closed,
            or None if state is unknown

        """
        return self._device and self._device.is_open


class XComfortMotionSensor(BinarySensorEntity):
    """Representation of an xComfort motion sensor."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, hub: XComfortHub, device: MotionSensor) -> None:
        """Initialize the motion binary sensor."""
        super().__init__()
        self.hub = hub
        self._device = device
        self._attr_unique_id = f"motion_{hub.identifier}_{device.device_id}"
        self._attr_device_info = get_motion_sensor_device_info(hub, device)
        self._attr_is_on = device.motion
        init_entity_lifecycle(self)

    async def async_added_to_hass(self):
        """Subscribe to motion updates."""
        await super().async_added_to_hass()
        mark_entity_added(self)
        subscribe_observable(
            self, self._device.state, self._state_change, "device.state"
        )

    def _state_change(self, motion: bool | None):
        """Handle motion state changes from the device."""
        self._attr_is_on = motion
        schedule_state_update_safely(self, "device.state")


class XComfortWaterSensor(BinarySensorEntity):
    """Representation of an xComfort water sensor (CWGA-0D/01)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    def __init__(self, hub: XComfortHub, device: WaterSensor) -> None:
        """Initialize the water binary sensor."""
        super().__init__()
        self.hub = hub
        self._device = device
        self._attr_unique_id = f"water_{hub.identifier}_{device.device_id}"
        self._attr_device_info = get_water_sensor_device_info(hub, device)
        self._attr_is_on = device.water_detected
        init_entity_lifecycle(self)

    async def async_added_to_hass(self):
        """Subscribe to water state updates."""
        await super().async_added_to_hass()
        mark_entity_added(self)
        subscribe_observable(
            self, self._device.state, self._state_change, "device.state"
        )

    def _state_change(self, water_detected: bool | None):
        """Handle water state changes from the device."""
        self._attr_is_on = water_detected
        schedule_state_update_safely(self, "device.state")

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return when the bridge last reported a water state change."""
        if self._device.last_changed is None:
            return {}
        return {"last_changed_at": self._device.last_changed}


class XComfortBinaryInputSensor(BinarySensorEntity):
    """Contact state of an xComfort binary input channel.

    No device class: the bridge doesn't know what is wired to the input or
    whether the contact is normally open or closed, so users pick the
    device class ("Show as") in Home Assistant.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        hub: XComfortHub,
        device: Rocker,
        comp: Comp,
        mode: ComponentMode,
        enabled_default: bool,
    ) -> None:
        """Initialize the binary input sensor."""
        super().__init__()
        self.hub = hub
        self._device = device
        self._attr_name = device.name
        self._attr_unique_id = f"binary_input_{hub.identifier}_{device.device_id}"
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_extra_state_attributes = {
            "input_mode": _BINARY_INPUT_MODE_NAMES[mode]
        }
        # Same identifier as event.py / the diagnostic sensors, so battery
        # and signal land on this device card.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"event_{DOMAIN}_comp_{comp.comp_id}")},
            name=comp.name,
            manufacturer="Eaton",
            model=_BINARY_INPUT_MODELS[comp.comp_type],
            sw_version=comp.payload.get("versionFW"),
            hw_version=comp.payload.get("versionHW"),
            via_device=(DOMAIN, hub.hub_id),
        )
        self._attr_is_on = device.contact_state
        init_entity_lifecycle(self)

    async def async_added_to_hass(self):
        """Subscribe to channel state updates."""
        await super().async_added_to_hass()
        mark_entity_added(self)
        subscribe_observable(
            self, self._device.state, self._state_change, "device.state"
        )

    def _state_change(self, _state) -> None:
        """Re-read the strictly parsed contact state on every update."""
        self._attr_is_on = self._device.contact_state
        schedule_state_update_safely(self, "device.state")
