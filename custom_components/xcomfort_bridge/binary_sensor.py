"""Binary sensor platform for xComfort integration with Home Assistant."""
import logging

from xcomfort.devices import DoorSensor, DoorWindowSensor, Rocker, WindowSensor

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)

x = 123


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
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

        devices = hub.devices
        sensors = []

        # Create a generator expression and extend the list with it
        sensors.extend(
            XComfortDoorWindowSensor(hub, device)
            for device in devices
            if isinstance(device, DoorWindowSensor)
        )
        sensors.extend(
            XComfortRockerSensor(hass, hub, device)
            for device in devices
            if isinstance(device, Rocker)
        )

        _LOGGER.debug("Added %s binary sensors", len(sensors))
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

    async def async_added_to_hass(self):
        """Run when entity is added to Home Assistant.

        Sets up state change subscription if device state exists.

        """
        if self._device.state is not None:
            self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state: bool):
        """Handle state changes from the device.

        Args:
            state: New state value (True for open, False for closed)

        """
        self._attr_state = state
        self.schedule_update_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on.

        Returns:
            True if the sensor detects the door/window is open, False if closed,
            or None if state is unknown

        """
        return self._device and self._device.is_open

class XComfortRockerSensor(BinarySensorEntity):
    """Entity class for xComfort rockers."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Rocker) -> None:
        """Initialize the rock entity.

        Args:
            hass: HomeAssistant instance
            hub: XComfortHub instance
            device: Rocker device instance

        """
        super().__init__()
        self._attr_name = device.name

        self.hass = hass
        self.hub = hub

        self._device = device
        self._name = device.name
        self._state = None
        self.device_id = device.device_id

        self._unique_id = f"rocker_{DOMAIN}_{device.device_id}"

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        self._device.state.subscribe(self._state_change)

    def _state_change(self, state) -> None:
        """Handle state changes from the device."""
        self._state = state
        should_update = self._state is not None

        if should_update:
            self.schedule_update_ha_state()
            # Emit event to enable stateless automation, since
            # actual switch state may be same as before
            self.hass.bus.fire(self._unique_id, {"on": state})

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._state

    @property
    def name(self) -> str:
        """Return the display name of this switch."""
        return self._device.name_with_controlled

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Return if the entity should be polled for state updates."""
        return False
