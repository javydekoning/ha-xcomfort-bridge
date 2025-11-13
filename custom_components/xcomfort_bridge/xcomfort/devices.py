"""Devices module for xComfort integration."""

import logging

import rx

from .constants import ComponentTypes, Messages, ShadeOperationState

_LOGGER = logging.getLogger(__name__)


class DeviceState:
    """Base device state class."""

    def __init__(self, payload):
        """Initialize device state with payload."""
        self.raw = payload

    def __str__(self):
        """Return string representation of device state."""
        return f"DeviceState({self.raw})"


class LightState(DeviceState):
    """Light device state."""

    def __init__(self, switch, dimmvalue, payload):
        """Initialize light state."""
        DeviceState.__init__(self, payload)
        self.switch = switch
        self.dimmvalue = dimmvalue

    def __str__(self):
        """Return string representation of light state."""
        return f"LightState({self.switch}, {self.dimmvalue})"

    __repr__ = __str__


class RcTouchState(DeviceState):
    """RcTouch device state."""

    def __init__(self, temperature, humidity, payload):
        """Initialize RcTouch state."""
        DeviceState.__init__(self, payload)
        self.temperature = temperature
        self.humidity = humidity

    def __str__(self):
        """Return string representation of RcTouch state."""
        return f"RcTouchState({self.temperature}, {self.humidity})"

    __repr__ = __str__


class RockerSensorState(DeviceState):
    """Rocker with sensor state."""

    def __init__(self, is_on, temperature, humidity, payload):
        """Initialize rocker sensor state."""
        DeviceState.__init__(self, payload)
        self.is_on = is_on
        self.temperature = temperature
        self.humidity = humidity

    def __str__(self):
        """Return string representation of rocker sensor state."""
        return f"RockerSensorState(is_on={self.is_on}, temp={self.temperature}, humidity={self.humidity})"

    __repr__ = __str__


class HeaterState(DeviceState):
    """Heater device state."""

    def __init__(self, payload):
        """Initialize heater state."""
        DeviceState.__init__(self, payload)

    def __str__(self):
        """Return string representation of heater state."""
        return f"HeaterState({self.payload})"

    __repr__ = __str__


class ShadeState(DeviceState):
    """Shade device state."""

    def __init__(self):
        """Initialize shade state."""
        self.raw = {}
        self.current_state: int | None = None
        self.is_safety_enabled: bool | None = None
        self.position: int | None = None

    def update_from_partial_state_update(self, payload: dict) -> None:
        """Update state from partial state update."""
        self.raw.update(payload)

        if (current_state := payload.get("curstate")) is not None:
            self.current_state = current_state

        if (safety := payload.get("shSafety")) is not None:
            self.is_safety_enabled = safety != 0

        if (position := payload.get("shPos")) is not None:
            self.position = position

    @property
    def is_closed(self) -> bool | None:
        """Check if shade is closed."""
        if (self.position is None) or (0 < self.position < 100):
            # It's not fully closed or open and can move both ways, or we don't know
            return None

        # It's fully extended, i.e. "closed"
        return self.position == 100

    def __str__(self) -> str:
        """Return string representation of shade state."""
        return f"ShadeState(current_state={self.current_state} is_safety_enabled={self.is_safety_enabled} position={self.position} raw={self.raw})"


class BridgeDevice:
    """Base bridge device class."""

    def __init__(self, bridge, device_id, name):
        """Initialize bridge device."""
        self.bridge = bridge
        self.device_id = device_id
        self.name = name

        self.state = rx.subject.BehaviorSubject(None)

    def handle_state(self, payload):
        """Handle state updates."""
        self.state.on_next(DeviceState(payload))


class Light(BridgeDevice):
    """Light device class."""

    def __init__(self, bridge, device_id, name, dimmable):
        """Initialize light device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.dimmable = dimmable

    def interpret_dimmvalue_from_payload(self, switch, payload):
        """Interpret dimmvalue from payload."""
        if not self.dimmable:
            return 99

        if not switch:
            return self.state.value.dimmvalue if self.state.value is not None else 99

        # Return dimmvalue if present, otherwise default to 99 (full brightness)
        return payload.get("dimmvalue", 99)

    def handle_state(self, payload):
        """Handle light state updates."""
        # Only process if this is a switch state update
        if "switch" not in payload:
            _LOGGER.debug("Light %s received non-switch payload, ignoring: %s", self.name, payload)
            return

        switch = payload["switch"]
        dimmvalue = self.interpret_dimmvalue_from_payload(switch, payload)
        _LOGGER.debug("Light %s state update: switch=%s, dimmvalue=%s", self.name, switch, dimmvalue)
        self.state.on_next(LightState(switch, dimmvalue, payload))

    async def switch(self, switch: bool):
        """Switch light on/off."""
        _LOGGER.debug("Switching light %s: %s", self.name, "ON" if switch else "OFF")
        await self.bridge.switch_device(self.device_id, {"switch": switch})

    async def dimm(self, value: int):
        """Set dimming value."""
        value = max(0, min(99, value))
        _LOGGER.debug("Setting light %s dim value to %s", self.name, value)
        await self.bridge.slide_device(self.device_id, {"dimmvalue": value})

    def __str__(self):
        """Return string representation of light device."""
        return f'Light({self.device_id}, "{self.name}", dimmable: {self.dimmable}, state:{self.state.value})'

    __repr__ = __str__


class RcTouch(BridgeDevice):
    """RcTouch device class."""

    def __init__(self, bridge, device_id, name, comp_id):
        """Initialize RcTouch device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.comp_id = comp_id

    def handle_state(self, payload):
        """Handle RcTouch state updates."""
        _LOGGER.debug("RcTouch %s: Received payload: %s", self.name, payload)
        temperature = None
        humidity = None
        if "info" in payload:
            for info in payload["info"]:
                if info["text"] == "1222":
                    temperature = float(info["value"])
                if info["text"] == "1223":
                    humidity = float(info["value"])

        if temperature is not None and humidity is not None:
            _LOGGER.debug("RcTouch %s state update: temp=%s°C, humidity=%s%%",
                         self.name, temperature, humidity)
            self.state.on_next(RcTouchState(temperature, humidity, payload))


class Heater(BridgeDevice):
    """Heater device class."""

    def __init__(self, bridge, device_id, name, comp_id):
        """Initialize heater device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.comp_id = comp_id


class Shade(BridgeDevice):
    """Shade device class."""

    def __init__(self, bridge, device_id, name, comp_id, payload):
        """Initialize shade device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.component = bridge._comps.get(comp_id)  # noqa: SLF001
        self.payload = payload

        # We get partial updates of shade state across different state updates, so
        # we aggregate them via this object
        self.__shade_state = ShadeState()

        self.comp_id = comp_id

    @property
    def supports_go_to(self) -> bool | None:
        """Check if shade supports go to position."""
        # "go to" is whether a specific position can be set, i.e. 50 meaning halfway down
        # Not all actuators support this, even if they can be stopped at arbitrary positions.
        if (component := self.bridge._comps.get(self.comp_id)) is not None:  # noqa: SLF001
            return component.comp_type == 86 and self.payload.get("shRuntime") == 1
        return None

    def handle_state(self, payload):
        """Handle shade state updates."""
        self.__shade_state.update_from_partial_state_update(payload)
        _LOGGER.debug("Shade %s state update: position=%s, current_state=%s, safety=%s",
                     self.name, self.__shade_state.position,
                     self.__shade_state.current_state, self.__shade_state.is_safety_enabled)
        self.state.on_next(self.__shade_state)

    async def send_state(self, state, **kw):
        """Send shade state to bridge."""
        if self.__shade_state.is_safety_enabled:
            # Do not trigger changes if safety is on. The official xcomfort client does
            # this check in the client, so we do that too just to be safe.
            _LOGGER.warning("Shade %s: Cannot send state, safety is enabled", self.name)
            return

        _LOGGER.debug("Shade %s: Sending state %s with args %s", self.name, state, kw)
        await self.bridge.send_message(
            Messages.SET_DEVICE_SHADING_STATE,
            {"deviceId": self.device_id, "state": state, **kw},
        )

    async def move_down(self):
        """Move shade down."""
        _LOGGER.debug("Shade %s: Moving down", self.name)
        await self.send_state(ShadeOperationState.CLOSE)

    async def move_up(self):
        """Move shade up."""
        _LOGGER.debug("Shade %s: Moving up", self.name)
        await self.send_state(ShadeOperationState.OPEN)

    async def move_stop(self):
        """Stop shade movement."""
        if self.__shade_state.is_safety_enabled:
            _LOGGER.warning("Shade %s: Cannot stop, safety is enabled", self.name)
            return

        _LOGGER.debug("Shade %s: Stopping", self.name)
        await self.send_state(ShadeOperationState.STOP)

    async def move_to_position(self, position: int):
        """Move shade to specific position."""
        assert self.supports_go_to and 0 <= position <= 100
        _LOGGER.debug("Shade %s: Moving to position %s", self.name, position)
        await self.send_state(ShadeOperationState.GO_TO, value=position)

    def __str__(self) -> str:
        """Return string representation of shade device."""
        return f"<Shade device_id={self.device_id} name={self.name} state={self.state} supports_go_to={self.supports_go_to}>"


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
            _LOGGER.debug("Door/Window sensor %s state update: %s",
                         self.name, "CLOSED" if self.is_closed else "OPEN")

        self.state.on_next(self.is_closed)


class WindowSensor(DoorWindowSensor):
    """Window sensor device class."""



class DoorSensor(DoorWindowSensor):
    """Door sensor device class."""



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
        1. Try device_id + 1 (pattern observed: Rocker=14, Sensor=15)
        2. Try same comp_id as fallback
        """
        if self._sensor_device is not None:
            return  # Already found and subscribed

        _LOGGER.debug("Rocker %s (device_id=%s, comp_id=%s) searching for companion sensor device...",
                     self.name, self.device_id, self.comp_id)

        # Strategy 1: Try device_id + 1 (most common pattern)
        sensor_device_id = self.device_id + 1
        candidate = self.bridge._devices.get(sensor_device_id)  # noqa: SLF001

        if candidate is not None:
            _LOGGER.info("Rocker %s found companion sensor device by device_id+1: %s (device_id=%s, type=%s, has_comp_id=%s)",
                        self.name, candidate.name, candidate.device_id,
                        type(candidate).__name__, hasattr(candidate, 'comp_id'))
            if hasattr(candidate, 'comp_id'):
                _LOGGER.debug("  -> Sensor device comp_id: %s", candidate.comp_id)

            self._sensor_device = candidate
            # Subscribe to its state updates
            candidate.state.subscribe(lambda state: self._on_sensor_device_update(state))
            return

        # Strategy 2: Look for other devices with the same comp_id
        for device in self.bridge._devices.values():  # noqa: SLF001
            if (device.device_id != self.device_id and
                hasattr(device, 'comp_id') and
                device.comp_id == self.comp_id):
                # Found a companion device in the same component
                _LOGGER.info("Rocker %s found companion sensor device by comp_id: %s (device_id=%s)",
                            self.name, device.name, device.device_id)
                self._sensor_device = device
                # Subscribe to its state updates
                device.state.subscribe(lambda state: self._on_sensor_device_update(state))
                return

        # Not found yet - will retry on first state update
        _LOGGER.debug("Rocker %s: companion sensor device not found yet. Available devices: %s",
                     self.name, list(self.bridge._devices.keys()))  # noqa: SLF001

    def _on_sensor_device_update(self, state) -> None:
        """Handle sensor device state updates."""
        _LOGGER.debug("Rocker %s received sensor device update: state=%s, has_raw=%s",
                     self.name, type(state).__name__, hasattr(state, 'raw') if state else False)

        if state is None:
            return

        # Handle different state types
        if not hasattr(state, 'raw'):
            _LOGGER.debug("Rocker %s sensor state has no 'raw' attribute, type is %s",
                         self.name, type(state).__name__)
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

                _LOGGER.debug("Rocker %s checking info item: text=%s, value=%s",
                             self.name, text, value_str)

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

            _LOGGER.info("Rocker %s sensor values updated: temp=%s°C, humidity=%s%%",
                        self.name, self.temperature, self.humidity)

            if self.temperature is not None or self.humidity is not None:
                self.state.on_next(RockerSensorState(self.is_on, self.temperature,
                                                     self.humidity, self.payload))
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
                _LOGGER.debug("Rocker %s component info update: %s",
                            self.name, comp_payload["info"])

    def handle_state(self, payload, broadcast: bool = True) -> None:
        """Handle rocker state updates."""
        self.payload.update(payload)
        self.is_on = bool(payload["curstate"])

        # For multisensor rockers, include sensor data in state
        if self.has_sensors:
            # Try to find sensor device if we haven't found it yet
            if self._sensor_device is None:
                self._find_and_subscribe_sensor_device()

            _LOGGER.debug("Rocker %s state update: %s, temp=%s°C, humidity=%s%%",
                        self.name, "ON" if self.is_on else "OFF",
                        self.temperature, self.humidity)
            if broadcast:
                # Always broadcast with RockerSensorState for multisensor rockers
                self.state.on_next(RockerSensorState(self.is_on, self.temperature,
                                                     self.humidity, payload))
        else:
            _LOGGER.debug("Rocker %s state update: %s", self.name, "ON" if self.is_on else "OFF")
            if broadcast:
                self.state.on_next(self.is_on)

    def __str__(self):
        """Return string representation of rocker device."""
        if self.has_sensors:
            return f'Rocker({self.device_id}, "{self.name}", is_on: {self.is_on}, temp: {self.temperature}, humidity: {self.humidity})'
        return f'Rocker({self.device_id}, "{self.name}", is_on: {self.is_on} payload: {self.payload})'
