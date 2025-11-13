"""Support for Xcomfort sensors."""

from __future__ import annotations

import logging
import math
import time
from typing import cast

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub
from .xcomfort.bridge import Room
from .xcomfort.devices import RcTouch, Rocker

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up xComfort sensor devices."""
    hub = XComfortHub.get_hub(hass, entry)

    # Get IP address from config
    ip = str(entry.data.get(CONF_IP_ADDRESS))

    # Add hub diagnostic sensors immediately
    hub_sensors = [
        XComfortHubSensor(hub, entry, "hub_id", "Hub ID", "mdi:identifier"),
        XComfortHubSensor(hub, entry, "firmware_version", "Firmware Version", "mdi:chip"),
        XComfortHubSensor(hub, entry, "bridge_name", "Bridge Name", "mdi:bridge"),
        XComfortHubSensor(hub, entry, "bridge_model", "Bridge Model", "mdi:devices"),
        XComfortHubSensor(hub, entry, "ip_address", "IP Address", "mdi:ip-network", ip),
        XComfortHubSensor(hub, entry, "home_scenes_count", "Scenes Count", "mdi:script-text-outline"),
    ]
    async_add_entities(hub_sensors)

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
                _LOGGER.debug("Adding temperature and humidity sensors for RcTouch device %s", device)
                sensors.append(XComfortRcTouchTemperatureSensor(hub, device))
                sensors.append(XComfortRcTouchHumiditySensor(hub, device))
            elif isinstance(device, Rocker) and device.has_sensors:
                _LOGGER.debug("Adding temperature and humidity sensors for multisensor Rocker %s", device)
                sensors.append(XComfortRockerTemperatureSensor(hub, device))
                sensors.append(XComfortRockerHumiditySensor(hub, device))

        _LOGGER.debug("Added %s sensor entities", len(sensors))
        async_add_entities(sensors)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class XComfortHubSensor(SensorEntity):
    """Sensor entity for xComfort hub diagnostics."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        hub: XComfortHub,
        entry: ConfigEntry,
        attribute: str,
        name: str,
        icon: str,
        value: str | None = None,
    ):
        """Initialize the hub sensor.

        Args:
            hub: XComfortHub instance
            entry: ConfigEntry instance
            attribute: Hub attribute to display (hub_id, firmware_version, bridge_name, bridge_model, ip_address, or home_scenes_count)
            name: Display name for the sensor
            icon: MDI icon for the sensor
            value: Optional fixed value (for IP address)

        """
        self.hub = hub
        self._attribute = attribute
        self._fixed_value = value
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{hub.hub_id}_{attribute}"

        # Link to the hub device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.hub_id)},
        )

    @property
    def native_value(self) -> str | None:
        """Return the current value of the sensor."""
        # Return fixed value if provided (for IP address)
        if self._fixed_value is not None:
            return self._fixed_value
        # Otherwise get from hub attribute
        return getattr(self.hub, self._attribute, None)


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
        self._attr_name = f"{self._room.name} Power"
        self._attr_unique_id = f"energy_{self._room.room_id}"
        self._unique_id = f"energy_{self._room.room_id}"
        self._state = None
        self._room.state.subscribe(lambda state: self._state_change(state))

        unique_id = f"climate_{DOMAIN}_{hub.identifier}-{room.room_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=self._room.name,
        )

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
        self._attr_name = f"{self._room.name} Energy"
        self._attr_unique_id = f"energy_kwh_{self._room.room_id}"
        self._unique_id = f"energy_kwh_{self._room.room_id}"
        self._state = None
        self._room.state.subscribe(lambda state: self._state_change(state))
        self._updateTime = time.monotonic()
        self._consumption = 0

        device_id = f"climate_{DOMAIN}_{hub.identifier}-{room.room_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=self._room.name,
        )

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
        self._consumption += power / 3600 / 1000 * timediff  # Calculate, in kWh, energy consumption since last update.
        self._updateTime = now

    @property
    def native_value(self):
        """Return the current value."""
        if self._state and self._state.power is not None:
            self.calculate(self._state.power)
            return self._consumption
        return None


class XComfortRcTouchTemperatureSensor(SensorEntity):
    """Entity class for xComfort RC Touch temperature sensors."""

    def __init__(self, hub: XComfortHub, device: RcTouch):
        """Initialize the temperature sensor entity.

        Args:
            hub: XComfortHub instance
            device: RcTouch device instance

        """
        self.entity_description = SensorEntityDescription(
            key="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            name="Temperature",
        )
        self._device = device
        self._attr_name = f"{self._device.name} Temperature"
        self._attr_unique_id = f"temperature_{self._device.name}_{self._device.device_id}"

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
        return self._state and self._state.temperature


class XComfortRcTouchHumiditySensor(SensorEntity):
    """Entity class for xComfort RC Touch humidity sensors."""

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
        self._attr_name = f"{self._device.name} Humidity"
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


class XComfortRockerTemperatureSensor(SensorEntity):
    """Entity class for xComfort Rocker multisensor temperature sensors."""

    def __init__(self, hub: XComfortHub, device: Rocker):
        """Initialize the temperature sensor entity.

        Args:
            hub: XComfortHub instance
            device: Rocker device instance with sensor capabilities

        """
        self.entity_description = SensorEntityDescription(
            key="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            name="Temperature",
        )
        self._device = device
        comp = device.bridge._comps.get(device.comp_id)  # noqa: SLF001
        comp_name = comp.name if comp else "Unknown"
        self._attr_name = f"{comp_name} Temperature"
        self._attr_unique_id = f"temperature_rocker_{device.device_id}"

        # Link to the same device as the event entity
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"event_{DOMAIN}_{device.device_id}")},
        )

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
        if self._state is None:
            return None
        # Handle both RockerSensorState and legacy bool states
        if hasattr(self._state, 'temperature'):
            return self._state.temperature
        return None


class XComfortRockerHumiditySensor(SensorEntity):
    """Entity class for xComfort Rocker multisensor humidity sensors."""

    def __init__(self, hub: XComfortHub, device: Rocker):
        """Initialize the humidity sensor entity.

        Args:
            hub: XComfortHub instance
            device: Rocker device instance with sensor capabilities

        """
        self.entity_description = SensorEntityDescription(
            key="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            name="Humidity",
        )
        self._device = device
        comp = device.bridge._comps.get(device.comp_id)  # noqa: SLF001
        comp_name = comp.name if comp else "Unknown"
        self._attr_name = f"{comp_name} Humidity"
        self._attr_unique_id = f"humidity_rocker_{device.device_id}"

        # Link to the same device as the event entity
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"event_{DOMAIN}_{device.device_id}")},
        )

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
        if self._state is None:
            return None
        # Handle both RockerSensorState and legacy bool states
        if hasattr(self._state, 'humidity'):
            return self._state.humidity
        return None
