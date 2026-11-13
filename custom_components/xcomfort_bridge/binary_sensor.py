"""Binary sensor platform for xComfort integration with Home Assistant."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device_info import get_motion_sensor_device_info
from .entity_lifecycle import (
    init_entity_lifecycle,
    mark_entity_added,
    schedule_state_update_safely,
    subscribe_observable,
)
from .hub import XComfortHub
from .xcomfort.devices import DoorSensor, MotionSensor, WindowSensor

_LOGGER = logging.getLogger(__name__)


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
