"""Device state classes for xComfort integration."""


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

    def __init__(self, switch, dimmvalue, power, payload):
        """Initialize light state."""
        DeviceState.__init__(self, payload)
        self.switch = switch
        self.dimmvalue = dimmvalue
        self.power = power

    def __str__(self):
        """Return string representation of light state."""
        return f"LightState({self.switch}, {self.dimmvalue}, power={self.power})"

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

    def __init__(self, device_temperature, heating_demand, power, payload):
        """Initialize heater state."""
        DeviceState.__init__(self, payload)
        self.device_temperature = device_temperature
        self.heating_demand = heating_demand
        self.power = power

    def __str__(self):
        """Return string representation of heater state."""
        return f"HeaterState(temp={self.device_temperature}°C, demand={self.heating_demand}%, power={self.power}W)"

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
