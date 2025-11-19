"""Rocker device for xComfort integration."""

import logging

from .constants import ComponentTypes
from .device_base import BridgeDevice
from .device_states import RockerSensorState

_LOGGER = logging.getLogger(__name__)


class Rocker(BridgeDevice):
    """Rocker device class."""

    def __init__(self, bridge, device_id, name, comp_id, payload):
        """Initialize rocker device."""
        BridgeDevice.__init__(self, bridge, device_id, name)
        self.comp_id = comp_id
        self.payload = payload
        self.is_on: bool | None = None
        self.temperature: float | None = None
        self.humidity: float | None = None
        self._sensor_device = None
        if "curstate" in payload:
            self.is_on = bool(payload["curstate"])

        # Subscribe to component state updates if this is a multisensor
        if self.has_sensors:
            comp = self.bridge._comps.get(self.comp_id)  # noqa: SLF001
            comp.state.subscribe(lambda _: self._on_component_update())
            # Find and subscribe to companion sensor device
            self._find_and_subscribe_sensor_device()

    @property
    def name_with_controlled(self) -> str:
        """Name of Rocker, with the names of controlled devices in parens."""
        names_of_controlled: set[str] = set()
        for device_id in self.payload.get("controlId", []):
            device = self.bridge._devices.get(device_id)  # noqa: SLF001
            if device:
                names_of_controlled.add(device.name)

        return f"{self.name} ({', '.join(sorted(names_of_controlled))})"

    @property
    def has_sensors(self) -> bool:
        """Check if this rocker has sensor capabilities."""
        comp = self.bridge._comps.get(self.comp_id)  # noqa: SLF001
        # Check if component is any multi sensor push button type
        return comp is not None and comp.comp_type in (
            ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_1_CHANNEL,
            ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_2_CHANNEL,
            ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_4_CHANNEL,
        )

    def _find_and_subscribe_sensor_device(self) -> None:
        """Find companion sensor device and subscribe to its updates.

        The companion device might not be created yet during initialization,
        so this method can be called multiple times.

        Search strategy:
        - Find sensor with the same comp_id
        """
        if self._sensor_device is not None:
            return  # Already found and subscribed

        _LOGGER.debug(
            "Rocker %s (device_id=%s, comp_id=%s) searching for companion sensor device...",
            self.name,
            self.device_id,
            self.comp_id,
        )

        for device in self.bridge._devices.values():  # noqa: SLF001
            if device.device_id != self.device_id and hasattr(device, "comp_id") and device.comp_id == self.comp_id:
                # Found a companion device in the same component
                _LOGGER.info(
                    "Rocker %s found companion sensor device by comp_id: %s (device_id=%s)",
                    self.name,
                    device.name,
                    device.device_id,
                )
                self._sensor_device = device
                # Subscribe to its state updates
                device.state.subscribe(lambda state: self._on_sensor_device_update(state))
                return

        # Not found yet - will retry on first state update
        _LOGGER.debug(
            "Rocker %s: companion sensor device not found yet. Available devices: %s",
            self.name,
            list(self.bridge._devices.keys()),  # noqa: SLF001
        )

    def _on_sensor_device_update(self, state) -> None:
        """Handle sensor device state updates."""
        _LOGGER.debug(
            "Rocker %s received sensor device update: state=%s, has_raw=%s",
            self.name,
            type(state).__name__,
            hasattr(state, "raw") if state else False,
        )

        if state is None:
            return

        # Handle different state types
        if not hasattr(state, "raw"):
            _LOGGER.debug("Rocker %s sensor state has no 'raw' attribute, type is %s", self.name, type(state).__name__)
            return

        payload = state.raw
        _LOGGER.debug("Rocker %s sensor device payload: %s", self.name, payload)

        temperature = None
        humidity = None

        # Parse sensor data from device info array
        if "info" in payload:
            _LOGGER.debug("Rocker %s parsing info array: %s", self.name, payload["info"])
            for info in payload["info"]:
                text = info.get("text")
                value_str = info.get("value")

                _LOGGER.debug("Rocker %s checking info item: text=%s, value=%s", self.name, text, value_str)

                if not value_str:
                    continue

                try:
                    value = float(value_str)
                    # Use RC Touch codes: 1222 = temp, 1223 = humidity
                    if text == "1222":
                        temperature = value
                        _LOGGER.debug("Rocker %s found temperature: %s°C", self.name, temperature)
                    elif text == "1223":
                        humidity = value
                        _LOGGER.debug("Rocker %s found humidity: %s%%", self.name, humidity)
                except (ValueError, TypeError) as e:
                    _LOGGER.debug("Rocker %s error parsing value: %s", self.name, e)
        else:
            _LOGGER.debug("Rocker %s sensor device payload has no 'info' key", self.name)

        # Update sensor values if we got them
        if temperature != self.temperature or humidity != self.humidity:
            self.temperature = temperature
            self.humidity = humidity

            _LOGGER.info(
                "Rocker %s sensor values updated: temp=%s°C, humidity=%s%%", self.name, self.temperature, self.humidity
            )

            if self.temperature is not None or self.humidity is not None:
                self.state.on_next(RockerSensorState(self.is_on, self.temperature, self.humidity, self.payload))
        else:
            _LOGGER.debug("Rocker %s sensor values unchanged", self.name)

    def extract_sensor_data_from_companion(self) -> tuple[float | None, float | None]:
        """Extract temperature and humidity from companion sensor device.

        For multisensor rockers, sensor data comes from a companion device
        with the same comp_id, using info codes 1222 (temp) and 1223 (humidity).
        """
        if self._sensor_device is None:
            return None, None

        # Return current values if we have them
        return self.temperature, self.humidity

    def _on_component_update(self) -> None:
        """Handle component state updates.

        Component updates are logged for debugging but sensor data comes
        from the companion sensor device, not the component itself.
        """
        if not self.has_sensors:
            return

        # Try to find sensor device if we haven't found it yet
        if self._sensor_device is None:
            self._find_and_subscribe_sensor_device()

        # Log component info for debugging
        comp = self.bridge._comps.get(self.comp_id)  # noqa: SLF001
        if comp and comp.state.value:
            comp_payload = comp.state.value.raw
            if "info" in comp_payload:
                _LOGGER.debug("Rocker %s component info update: %s", self.name, comp_payload["info"])

    def handle_state(self, payload, broadcast: bool = True) -> None:
        """Handle rocker state updates."""
        self.payload.update(payload)
        self.is_on = bool(payload["curstate"])

        # For multisensor rockers, include sensor data in state
        if self.has_sensors:
            # Try to find sensor device if we haven't found it yet
            if self._sensor_device is None:
                self._find_and_subscribe_sensor_device()

            _LOGGER.debug(
                "Rocker %s state update: %s, temp=%s°C, humidity=%s%%",
                self.name,
                "ON" if self.is_on else "OFF",
                self.temperature,
                self.humidity,
            )
            if broadcast:
                # Always broadcast with RockerSensorState for multisensor rockers
                self.state.on_next(RockerSensorState(self.is_on, self.temperature, self.humidity, payload))
        else:
            _LOGGER.debug("Rocker %s state update: %s", self.name, "ON" if self.is_on else "OFF")
            if broadcast:
                self.state.on_next(self.is_on)

    def __str__(self):
        """Return string representation of rocker device."""
        if self.has_sensors:
            return f'Rocker({self.device_id}, "{self.name}", is_on: {self.is_on}, temp: {self.temperature}, humidity: {self.humidity})'
        return f'Rocker({self.device_id}, "{self.name}", is_on: {self.is_on} payload: {self.payload})'

