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
from .xcomfort.constants import ComponentTypes
from .xcomfort.devices import RcTouch, Rocker

_LOGGER = logging.getLogger(__name__)

# Multi-channel component types that should be grouped into a single device
MULTI_CHANNEL_COMPONENTS = {
    ComponentTypes.PUSH_BUTTON_2_CHANNEL,
    ComponentTypes.PUSH_BUTTON_4_CHANNEL,
    ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_2_CHANNEL,
    ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_4_CHANNEL,
    ComponentTypes.REMOTE_CONTROL_2_CHANNEL,
}


def _is_multi_channel_component(comp_type: int) -> bool:
    """Check if a component type is multi-channel."""
    return comp_type in MULTI_CHANNEL_COMPONENTS


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

    # Add bridge state sensors
    _LOGGER.debug("Creating bridge state sensors for bridge %s (hub_id: %s)", hub.bridge_name or "Unknown", hub.hub_id)
    hub_sensors.append(XComfortBridgeHeatingOnSensor(hub))
    hub_sensors.append(XComfortBridgeLightsOnSensor(hub))
    hub_sensors.append(XComfortBridgeLoadsOnSensor(hub))
    hub_sensors.append(XComfortBridgeWindowsOpenSensor(hub))
    hub_sensors.append(XComfortBridgeDoorsOpenSensor(hub))
    hub_sensors.append(XComfortBridgePresenceSensor(hub))
    hub_sensors.append(XComfortBridgeShadesClosedSensor(hub))
    hub_sensors.append(XComfortBridgeWaterGuardSensor(hub))
    hub_sensors.append(XComfortBridgeCoolingOnSensor(hub))
    hub_sensors.append(XComfortBridgePowerSensor(hub))
    hub_sensors.append(XComfortBridgeOutsideTemperatureSensor(hub))
    _LOGGER.debug("Created %d bridge state sensors for bridge %s", 11, hub.bridge_name or hub.hub_id)

    async_add_entities(hub_sensors)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        devices = hub.devices

        _LOGGER.debug("Found %s xcomfort devices", len(list(devices)))

        sensors = []
        processed_multi_sensor_comps = set()  # Track which multi-sensor components we've processed

        # Add device-based sensors only (no room-based sensors)
        for device in devices:
            if isinstance(device, RcTouch):
                _LOGGER.debug("Adding temperature and humidity sensors for RcTouch device %s", device.name)
                sensors.append(XComfortRcTouchTemperatureSensor(hub, device))
                sensors.append(XComfortRcTouchHumiditySensor(hub, device))
            elif isinstance(device, Rocker) and device.has_sensors:
                comp = device.bridge._comps.get(device.comp_id)  # noqa: SLF001
                if not comp:
                    _LOGGER.warning("Rocker %s has sensors but no component, skipping", device.name)
                    continue

                # For multi-channel components, only create sensors once (not per button)
                if _is_multi_channel_component(comp.comp_type):
                    if comp.comp_id in processed_multi_sensor_comps:
                        _LOGGER.debug(
                            "Skipping sensor creation for %s - already created for component %s",
                            device.name,
                            comp.name,
                        )
                        continue
                    processed_multi_sensor_comps.add(comp.comp_id)
                    _LOGGER.debug(
                        "Adding temperature and humidity sensors for multi-channel multisensor component %s",
                        comp.name,
                    )
                else:
                    _LOGGER.debug("Adding temperature and humidity sensors for multisensor Rocker %s", device.name)

                sensors.append(XComfortRockerTemperatureSensor(hub, device))
                sensors.append(XComfortRockerHumiditySensor(hub, device))

        # Add room-based sensors
        rooms = hub.rooms
        _LOGGER.debug("Found %s xcomfort rooms", len(list(rooms)))

        for room in rooms:
            # Wait for room state to be initialized
            if room.state.value is not None and hasattr(room.state.value, "raw"):
                raw = room.state.value.raw

                # Always add integer sensors for lights, windows, doors
                if "lightsOn" in raw:
                    sensors.append(XComfortRoomLightsOnSensor(hub, room))
                if "windowsOpen" in raw:
                    sensors.append(XComfortRoomWindowsOpenSensor(hub, room))
                if "doorsOpen" in raw:
                    sensors.append(XComfortRoomDoorsOpenSensor(hub, room))

                # Add temperature and humidity if temperatureOnly property exists
                if "temperatureOnly" in raw:
                    if "temp" in raw:
                        sensors.append(XComfortRoomTemperatureSensor(hub, room))
                    if "humidity" in raw:
                        sensors.append(XComfortRoomHumiditySensor(hub, room))

                    # Add currentMode sensor if temperatureOnly is False
                    if raw.get("temperatureOnly") is False and "currentMode" in raw:
                        sensors.append(XComfortRoomCurrentModeSensor(hub, room))

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

        # Link to the climate device
        device_id = f"climate_{DOMAIN}_{hub.identifier}-{device.device_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
        )

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

        # Link to the climate device
        device_id = f"climate_{DOMAIN}_{hub.identifier}-{device.device_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
        )

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
        # For multi-channel components, use component-based device identifier
        if comp and _is_multi_channel_component(comp.comp_type):
            device_identifier = f"event_{DOMAIN}_comp_{device.comp_id}"
        else:
            device_identifier = f"event_{DOMAIN}_{device.device_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_identifier)},
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
        if hasattr(self._state, "temperature"):
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
        # For multi-channel components, use component-based device identifier
        if comp and _is_multi_channel_component(comp.comp_type):
            device_identifier = f"event_{DOMAIN}_comp_{device.comp_id}"
        else:
            device_identifier = f"event_{DOMAIN}_{device.device_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_identifier)},
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
        if hasattr(self._state, "humidity"):
            return self._state.humidity
        return None


class XComfortRoomSensorBase(SensorEntity):
    """Base class for xComfort room sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hub: XComfortHub,
        room: Room,
        key: str,
        name: str,
        icon: str,
        state_key: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
        value_fn=None,
    ):
        """Initialize the room sensor entity.

        Args:
            hub: XComfortHub instance
            room: Room instance
            key: Sensor key
            name: Sensor name
            icon: MDI icon
            state_key: Key to read from room state
            device_class: Sensor device class (optional)
            unit: Unit of measurement (optional)
            state_class: State class (optional)
            value_fn: Custom value function (optional)

        """
        self.entity_description = SensorEntityDescription(
            key=key,
            device_class=device_class,
            native_unit_of_measurement=unit,
            state_class=state_class,
            name=name,
        )
        self.hub = hub
        self._room = room
        self._state_key = state_key
        self._value_fn = value_fn
        self._attr_name = name
        self._attr_unique_id = f"room_{key}_{room.room_id}"
        self._attr_icon = icon
        self._state = None
        room.state.subscribe(lambda state: self._state_change(state))

        device_id = f"room_{DOMAIN}_{hub.identifier}_{room.room_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=room.name,
            manufacturer="Eaton",
            model="xComfort Room",
            via_device=(DOMAIN, hub.hub_id),
        )

    def _state_change(self, state):
        """Handle state changes from the room."""
        should_update = self._state is not None
        self._state = state
        if should_update:
            self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the current value."""
        if self._state is None or not hasattr(self._state, "raw"):
            return None

        value = self._state.raw.get(self._state_key)
        if self._value_fn:
            return self._value_fn(value, self._state.raw)
        return value


class XComfortBridgeSensorBase(SensorEntity):
    """Base class for xComfort bridge sensors."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hub: XComfortHub,
        key: str,
        name: str,
        icon: str,
        state_key: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        state_class: SensorStateClass | None = None,
        value_fn=None,
    ):
        """Initialize the bridge sensor entity.

        Args:
            hub: XComfortHub instance
            key: Sensor key
            name: Sensor name
            icon: MDI icon
            state_key: Key to read from bridge state
            device_class: Sensor device class (optional)
            unit: Unit of measurement (optional)
            state_class: State class (optional)
            value_fn: Custom value function (optional)

        """
        if device_class or unit or state_class:
            self.entity_description = SensorEntityDescription(
                key=key,
                device_class=device_class,
                native_unit_of_measurement=unit,
                state_class=state_class,
                name=name,
            )
        self.hub = hub
        self._state_key = state_key
        self._value_fn = value_fn
        self._attr_name = name
        self._attr_unique_id = f"{hub.hub_id}_{key}"
        self._attr_icon = icon
        self._state = None
        self._bridge_id = hub.hub_id

        # Subscribe to bridge state updates
        hub.bridge.bridge_state.subscribe(lambda state: self._state_change(state))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.hub_id)},
        )

    async def async_added_to_hass(self):
        """Run when entity is added to hass."""
        # Get current bridge state if available
        current_state = self.hub.bridge.bridge_state.value
        if current_state is not None:
            _LOGGER.debug(
                "Bridge sensor %s initializing with existing state for bridge %s", self._attr_name, self._bridge_id
            )
            self._state = current_state
            self.async_write_ha_state()

    def _state_change(self, state):
        """Handle state changes from the bridge."""
        if state is not None:
            _LOGGER.debug(
                "Bridge sensor %s (%s) received state update for bridge %s",
                self._attr_name,
                self._state_key,
                self._bridge_id,
            )

        should_update = self._state is not None
        self._state = state
        if should_update:
            self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the current value."""
        if self._state is None:
            _LOGGER.debug("Bridge sensor %s has no state yet (bridge %s)", self._attr_name, self._bridge_id)
            return None

        value = self._state.get(self._state_key)
        if self._value_fn:
            return self._value_fn(value)
        return value


# Room sensor factory functions
def XComfortRoomLightsOnSensor(hub: XComfortHub, room: Room):
    """Create a room lights on sensor."""
    return XComfortRoomSensorBase(hub, room, "lights_on", "Lights On", "mdi:lightbulb-on", "lightsOn")


def XComfortRoomWindowsOpenSensor(hub: XComfortHub, room: Room):
    """Create a room windows open sensor."""
    return XComfortRoomSensorBase(hub, room, "windows_open", "Windows Open", "mdi:window-open-variant", "windowsOpen")


def XComfortRoomDoorsOpenSensor(hub: XComfortHub, room: Room):
    """Create a room doors open sensor."""
    return XComfortRoomSensorBase(hub, room, "doors_open", "Doors Open", "mdi:door-open", "doorsOpen")


def XComfortRoomTemperatureSensor(hub: XComfortHub, room: Room):
    """Create a room temperature sensor."""
    return XComfortRoomSensorBase(
        hub,
        room,
        "temperature",
        "Temperature",
        None,
        "temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    )


def XComfortRoomHumiditySensor(hub: XComfortHub, room: Room):
    """Create a room humidity sensor."""
    return XComfortRoomSensorBase(
        hub,
        room,
        "humidity",
        "Humidity",
        None,
        "humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    )


def XComfortRoomCurrentModeSensor(hub: XComfortHub, room: Room):
    """Create a room current mode sensor."""

    def map_mode(value, raw):
        """Map mode value to friendly name."""
        current_mode = value or raw.get("mode")
        if current_mode == 1:
            return "Frost Protection"
        if current_mode == 2:
            return "Eco"
        if current_mode == 3:
            return "Comfort"
        return current_mode

    return XComfortRoomSensorBase(
        hub, room, "current_mode", "Current Mode", "mdi:thermostat", "currentMode", state_class=None, value_fn=map_mode
    )


# Bridge sensor factory functions
def XComfortBridgeHeatingOnSensor(hub: XComfortHub):
    """Create a bridge heating on sensor."""
    return XComfortBridgeSensorBase(hub, "heating_on", "Heating On", "mdi:radiator", "heatingOn")


def XComfortBridgeLightsOnSensor(hub: XComfortHub):
    """Create a bridge lights on sensor."""
    return XComfortBridgeSensorBase(hub, "lights_on", "Lights On", "mdi:lightbulb-on", "lightsOn")


def XComfortBridgeLoadsOnSensor(hub: XComfortHub):
    """Create a bridge loads on sensor."""
    return XComfortBridgeSensorBase(hub, "loads_on", "Loads On", "mdi:power-socket", "loadsOn")


def XComfortBridgeWindowsOpenSensor(hub: XComfortHub):
    """Create a bridge windows open sensor."""
    return XComfortBridgeSensorBase(hub, "windows_open", "Windows Open", "mdi:window-open-variant", "windowsOpen")


def XComfortBridgeDoorsOpenSensor(hub: XComfortHub):
    """Create a bridge doors open sensor."""
    return XComfortBridgeSensorBase(hub, "doors_open", "Doors Open", "mdi:door-open", "doorsOpen")


def XComfortBridgePresenceSensor(hub: XComfortHub):
    """Create a bridge presence sensor."""
    return XComfortBridgeSensorBase(hub, "presence", "Presence", "mdi:home-account", "presence")


def XComfortBridgeShadesClosedSensor(hub: XComfortHub):
    """Create a bridge shades closed sensor."""
    return XComfortBridgeSensorBase(hub, "shades_closed", "Shades Closed", "mdi:window-shutter", "shadsClosed")


def XComfortBridgeWaterGuardSensor(hub: XComfortHub):
    """Create a bridge water guard sensor."""
    return XComfortBridgeSensorBase(hub, "water_guard_off", "Water Guard Off", "mdi:water-off", "wgWaterOff")


def XComfortBridgeCoolingOnSensor(hub: XComfortHub):
    """Create a bridge cooling on sensor."""
    return XComfortBridgeSensorBase(hub, "cooling_on", "Cooling On", "mdi:snowflake", "coolingOn")


def XComfortBridgePowerSensor(hub: XComfortHub):
    """Create a bridge power sensor."""
    return XComfortBridgeSensorBase(
        hub,
        "power",
        "Power",
        None,
        "power",
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    )


def XComfortBridgeOutsideTemperatureSensor(hub: XComfortHub):
    """Create a bridge outside temperature sensor."""

    def filter_invalid_temp(value):
        """Filter out -100.0 (sensor not connected)."""
        return None if value == -100.0 else value

    return XComfortBridgeSensorBase(
        hub,
        "outside_temperature",
        "Outside Temperature",
        None,
        "tempOutside",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=filter_invalid_temp,
    )
