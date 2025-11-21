"""Devices module for xComfort integration.

This module serves as a backward compatibility layer, re-exporting all device classes
from their new modular locations. This allows existing code to continue importing
from this single module while the implementation is split across multiple files.
"""

# Re-export all state classes
# Re-export base device class
from .device_base import BridgeDevice

# Re-export device classes
from .device_climate import Heater, RcTouch
from .device_light import Light
from .device_rocker import Rocker
from .device_sensors import DoorSensor, DoorWindowSensor, WindowSensor
from .device_shade import Shade
from .device_states import (
    DeviceState,
    HeaterState,
    LightState,
    RcTouchState,
    RockerSensorState,
    ShadeState,
)

__all__ = [
    # Base class
    "BridgeDevice",
    # State classes
    "DeviceState",
    "DoorSensor",
    "DoorWindowSensor",
    "Heater",
    "HeaterState",
    # Device classes
    "Light",
    "LightState",
    "RcTouch",
    "RcTouchState",
    "Rocker",
    "RockerSensorState",
    "Shade",
    "ShadeState",
    "WindowSensor",
]
