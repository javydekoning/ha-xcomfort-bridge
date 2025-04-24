"""Support for Xcomfort sensors."""

from __future__ import annotations

import logging
import math
import time
from typing import cast

from xcomfort.bridge import Room
from xcomfort.devices import RcTouch

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up xComfort sensor devices."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        rooms = hub.rooms
        devices = hub.devices

        _LOGGER.debug("Found %s xcomfort rooms", len(rooms))
        _LOGGER.debug("Found %s xcomfort devices", len(devices))

        sensors = []
        for room in rooms:
            if room.state.value is not None:
                if room.state.value.power is not None:
                    _LOGGER.debug("Adding power sensors for room %s", room.name)
                    sensors.append(XComfortPowerSensor(hub, room))

                if room.state.value.temperature is not None:
                     _LOGGER.debug("Adding temperature sensor for room %s", room.name)
                    sensors.append(XComfortEnergySensor(hub, room))

        for device in devices:
            if isinstance(device, RcTouch):
                _LOGGER.debug("Adding humidity sensor for device %s", device)
                sensors.append(XComfortHumiditySensor(hub, device))

        _LOGGER.debug("Added %s rc touch units", len(sensors))
        async_add_entities(sensors)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class XComfortPowerSensor(SensorEntity):
    """Entity class for xComfort power sensors."""

    def __init__(self, hub: XComfortHub, room: Room):
        """Initialize the power sensor entity.

        Args:
            hub: XComfortHub instance
            room: Room instance

        """
        self.entity_description = SensorEntityDescription(
            key="current_consumption",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            name="Current consumption",
        )
        self.hub = hub
        self._room = room
        self._attr_name = self._room.name
        self._attr_unique_id = f"energy_{self._room.room_id}"
        self._state = None
        self._room.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        """Handle state changes from the device."""
        should_update = self._state is not None

        self._state = state
        if should_update:
            self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the current power consumption."""
        if self._state is None:
            return None
        return self._state and self._state.power


class XComfortEnergySensor(RestoreSensor):
    """Entity class for xComfort energy sensors."""

    def __init__(self, hub: XComfortHub, room: Room):
        """Initialize the energy sensor entity.

        Args:
            hub: XComfortHub instance
            room: Room instance

        """
        self.entity_description = SensorEntityDescription(
            key="energy_used",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            name="Energy consumption",
        )
        self.hub = hub
        self._room = room
        self._attr_name = self._room.name
        self._attr_unique_id = f"energy_kwh_{self._room.room_id}"
        self._state = None
        self._room.state.subscribe(lambda state: self._state_change(state))
        self._updateTime = time.monotonic()
        self._consumption = 0

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        savedstate = await self.async_get_last_sensor_data()
        if savedstate:
            self._consumption = cast("float", savedstate.native_value)

    def _state_change(self, state):
        should_update = self._state is not None
        self._state = state
        if should_update:
            self.async_write_ha_state()

    def calculate(self, power):
        """Calculate energy consumption since last update."""
        now = time.monotonic()
        timediff = math.floor(now - self._updateTime)  # number of seconds since last update
        self._consumption += (
            power / 3600 / 1000 * timediff
        )  # Calculate, in kWh, energy consumption since last update.
        self._updateTime = now

    @property
    def native_value(self):
        """Return the current value."""
        if self._state and self._state.power is not None:
            self.calculate(self._state.power)
            return self._consumption
        return None


class XComfortHumiditySensor(SensorEntity):
    """Entity class for xComfort humidity sensors."""

    def __init__(self, hub: XComfortHub, device: RcTouch):
        """Initialize the humidity sensor entity.

        Args:
            hub: XComfortHub instance
            device: RcTouch device instance

        """
        self.entity_description = SensorEntityDescription(
            key="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            name="Humidity",
        )
        self._device = device
        self._attr_name = self._device.name
        self._attr_unique_id = f"humidity_{self._device.name}_{self._device.device_id}"

        self.hub = hub
        self._state = None
        self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        should_update = self._state is not None

        self._state = state
        if should_update:
            self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the current value."""
        return self._state and self._state.humidity
