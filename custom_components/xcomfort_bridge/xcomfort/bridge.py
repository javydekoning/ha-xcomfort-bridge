"""Bridge module for xComfort integration."""

import asyncio
from enum import Enum
import logging

import aiohttp
import rx

from .comp import Comp, CompState  # noqa: F401
from .connection import SecureBridgeConnection, setup_secure_connection
from .constants import ClimateMode, ComponentTypes, DeviceTypes, Messages
from .devices import (
    BridgeDevice,
    DoorSensor,
    Heater,
    Light,
    RcTouch,
    Rocker,
    Shade,
    WindowSensor,
)

# Some HA code relies on bridge having imported these:
from .room import RctModeRange, Room, RoomState  # noqa: F401

_LOGGER = logging.getLogger(__name__)


class State(Enum):
    """Bridge state enumeration."""

    Uninitialized = 0
    Initializing = 1
    Ready = 2
    Closing = 10


class Bridge:
    """Main bridge class for xComfort communication."""

    def __init__(self, ip_address: str, authkey: str, session=None):
        """Initialize bridge with IP address and auth key."""
        self.ip_address = ip_address
        self.authkey = authkey

        if session is None:
            session = aiohttp.ClientSession()
            closeSession = True
        else:
            closeSession = False

        self._session = session
        self._closeSession = closeSession

        # Values determined from using setpoint slider in app.
        self.rctsetpointallowedvalues = {
            ClimateMode.FrostProtection: RctModeRange(5.0, 20.0),
            ClimateMode.Eco: RctModeRange(10.0, 30.0),
            ClimateMode.Comfort: RctModeRange(18.0, 40.0),
        }
        self._comps = {}
        self._devices = {}
        self._rooms = {}
        self.state = State.Uninitialized
        self.on_initialized = asyncio.Event()
        self.connection = None
        self.connection_subscription = None

        # Bridge device information
        self.bridge_id = None
        self.bridge_name = None
        self.bridge_type = None
        self.fw_version = None
        self.home_scenes_count = 0
        self.home_data = {}

        # Bridge state (for sensors)
        self.bridge_state = rx.subject.BehaviorSubject(None)

        self.logger = lambda x: _LOGGER.warning(x)

        _LOGGER.info("Initialized xComfort bridge for %s", ip_address)

    async def run(self):
        """Run the bridge main loop."""
        if self.state != State.Uninitialized:
            raise RuntimeError("Run can only be called once at a time")

        self.state = State.Initializing
        _LOGGER.info("Starting bridge main loop")

        while self.state != State.Closing:
            try:
                _LOGGER.debug("Connecting to bridge at %s", self.ip_address)
                await self._connect()
                _LOGGER.info("Connected to bridge, starting message pump")
                await self.connection.pump()

            except (ConnectionError, RuntimeError) as e:
                _LOGGER.error("Connection error: %r, retrying in 5 seconds", e)
                await asyncio.sleep(5)

            if self.connection_subscription is not None:
                self.connection_subscription.dispose()

        self.state = State.Uninitialized
        _LOGGER.info("Bridge main loop stopped")

    async def switch_device(self, device_id, message):
        """Switch a device on/off."""
        payload = {"deviceId": device_id}
        payload.update(message)
        _LOGGER.debug("Switching device %s with payload: %s", device_id, message)
        await self.send_message(Messages.ACTION_SWITCH_DEVICE, payload)

    async def slide_device(self, device_id, message):
        """Slide a device (dimmer/shade)."""
        payload = {"deviceId": device_id}
        payload.update(message)
        _LOGGER.debug("Sliding device %s with payload: %s", device_id, message)
        await self.send_message(Messages.ACTION_SLIDE_DEVICE, payload)

    async def send_message(self, message_type: Messages, message):
        """Send a message to the bridge."""
        _LOGGER.debug("Sending message type %s: %s", message_type.name, message)
        await self.connection.send_message(message_type, message)

    def _add_comp(self, comp):
        """Add a component to the bridge."""
        self._comps[comp.comp_id] = comp
        _LOGGER.debug("Added component: %s (type: %s)", comp.name, comp.comp_type)

    def _add_device(self, device):
        """Add a device to the bridge."""
        self._devices[device.device_id] = device
        _LOGGER.debug("Added device: %s (id: %s, type: %s)", device.name, device.device_id, type(device).__name__)

    def _add_room(self, room):
        """Add a room to the bridge."""
        self._rooms[room.room_id] = room
        _LOGGER.debug("Added room: %s (id: %s)", room.name, room.room_id)

    def _handle_SET_DEVICE_STATE(self, payload):
        """Handle device state updates."""
        try:
            device_id = payload["deviceId"]
            device = self._devices.get(device_id)

            if device is None:
                # Check if this is a virtual rocker for an RcTouch device
                potential_rctouch_id = device_id - 1
                potential_rctouch = self._devices.get(potential_rctouch_id)

                if potential_rctouch is not None and isinstance(potential_rctouch, RcTouch):
                    _LOGGER.debug(
                        "Redirecting state update for virtual rocker %s to RcTouch %s",
                        device_id,
                        potential_rctouch.name,
                    )
                    # Forward button state updates to RcTouch
                    potential_rctouch.handle_virtual_rocker_state(payload)
                    return

                _LOGGER.warning("Received state update for unknown device: %s", device_id)
                return

            _LOGGER.debug("Updating device state for %s: %s", device.name, payload)
            device.handle_state(payload)
        except KeyError:
            _LOGGER.warning("Received state update for unknown device: %s", payload.get("deviceId"))
            return

    def _handle_SET_STATE_INFO(self, payload):
        """Handle state info updates."""
        _LOGGER.debug("Handling state info update with %d items", len(payload["item"]))
        for item in payload["item"]:
            if "deviceId" in item:
                deviceId = item["deviceId"]
                device = self._devices.get(deviceId)
                if device:
                    _LOGGER.debug("State update for device %s: %s", device.name, item)
                    device.handle_state(item)
                else:
                    # Check if this is a virtual rocker for an RcTouch device
                    potential_rctouch_id = deviceId - 1
                    potential_rctouch = self._devices.get(potential_rctouch_id)

                    if potential_rctouch is not None and isinstance(potential_rctouch, RcTouch):
                        _LOGGER.debug(
                            "Redirecting state update for virtual rocker %s to RcTouch %s",
                            deviceId,
                            potential_rctouch.name,
                        )
                        # Forward button state updates to RcTouch
                        potential_rctouch.handle_virtual_rocker_state(item)
                        continue

                    _LOGGER.warning("Received state update for unknown device %s: %s", deviceId, item)

            elif "roomId" in item:
                roomId = item["roomId"]
                room = self._rooms.get(roomId)
                if room:
                    _LOGGER.debug("State update for room %s: %s", room.name, item)
                    room.handle_state(item)
                else:
                    _LOGGER.warning("Received state update for unknown room %s: %s", roomId, item)

            elif "compId" in item:
                compId = item["compId"]
                comp = self._comps.get(compId)
                if comp:
                    _LOGGER.debug("State update for component %s: %s", comp.name, item)
                    comp.handle_state(item)
                else:
                    _LOGGER.warning("Received state update for unknown component %s: %s", compId, item)

            else:
                _LOGGER.warning("Unknown state info item (no deviceId, roomId, or compId): %s", item)

    def _create_comp_from_payload(self, payload):
        """Create a component from payload data."""
        comp_id = payload["compId"]
        name = payload["name"]
        comp_type = payload["compType"]

        return Comp(self, comp_id, comp_type, name, payload)

    def _create_device_from_payload(self, payload):
        """Create a device from payload data."""
        device_id = payload["deviceId"]
        name = payload["name"]
        dev_type = payload["devType"]
        comp_id = payload["compId"]

        _LOGGER.debug("Creating device from payload: id=%s, name=%s, devType=%s", device_id, name, dev_type)

        if dev_type in (DeviceTypes.ACTUATOR_SWITCH, DeviceTypes.ACTUATOR_DIMM):
            if payload.get("usage") == 0:
                # If usage = 1 then it's configured as a "load",
                # and not as a light.
                dimmable = payload["dimmable"]
                _LOGGER.debug("Creating Light device (dimmable=%s)", dimmable)
                return Light(self, device_id, name, dimmable)

        elif dev_type == DeviceTypes.SHADING_ACTUATOR:
            _LOGGER.debug("Creating Shade device")
            return Shade(self, device_id, name, comp_id, payload)

        elif dev_type == DeviceTypes.HEATING_ACTUATOR:
            _LOGGER.debug("Creating Heater device")
            return Heater(self, device_id, name, comp_id)

        elif dev_type == DeviceTypes.RC_TOUCH:
            _LOGGER.debug("Creating RcTouch device")
            rctouch = RcTouch(self, device_id, name, comp_id)

            # Check if virtual rocker was already created (before RcTouch)
            # If so, remove it from devices list since it should not be separate
            virtual_rocker_id = device_id + 1
            if virtual_rocker_id in self._devices:
                virtual_rocker = self._devices[virtual_rocker_id]
                if isinstance(virtual_rocker, Rocker):
                    _LOGGER.info(
                        "Found pre-existing virtual rocker %s (id: %s) for RcTouch %s (id: %s) - removing separate device",
                        virtual_rocker.name,
                        virtual_rocker_id,
                        name,
                        device_id,
                    )
                    del self._devices[virtual_rocker_id]

            return rctouch

        elif dev_type == DeviceTypes.SWITCH:
            component: Comp | None = self._comps.get(comp_id)
            if component and component.comp_type == ComponentTypes.DOOR_WINDOW_SENSOR:
                if component.payload.get("mode") == "1310":
                    _LOGGER.debug("Creating DoorSensor device")
                    return DoorSensor(self, device_id, name, comp_id, payload)
                _LOGGER.debug("Creating WindowSensor device")
                return WindowSensor(self, device_id, name, comp_id, payload)

        elif dev_type == DeviceTypes.ROCKER:
            # Check if this is a virtual rocker for an RcTouch device
            # RcTouch device ID is always rocker_id - 1
            potential_rctouch_id = device_id - 1
            potential_rctouch = self._devices.get(potential_rctouch_id)

            if potential_rctouch is not None and isinstance(potential_rctouch, RcTouch):
                _LOGGER.info(
                    "Rocker device %s (id: %s) is a virtual rocker for RcTouch %s (id: %s) - skipping separate device creation",
                    name,
                    device_id,
                    potential_rctouch.name,
                    potential_rctouch_id,
                )
                # Don't create a separate device - this rocker belongs to the RcTouch
                return None

            # What Xcomfort calls a rocker HomeAssistant (and most humans) call a
            # switch
            _LOGGER.debug("Creating Rocker device")
            return Rocker(self, device_id, name, comp_id, payload)

        _LOGGER.debug("Creating generic BridgeDevice (unrecognized device type)")
        return BridgeDevice(self, device_id, name)

    def _create_room_from_payload(self, payload):
        """Create a room from payload data."""
        room_id = payload["roomId"]
        name = payload["name"]

        return Room(self, room_id, name)

    def _handle_comp_payload(self, payload):
        """Handle component payload."""
        comp_id = payload["compId"]

        comp = self._comps.get(comp_id)

        if comp is None:
            comp = self._create_comp_from_payload(payload)

            if comp is None:
                return

            self._add_comp(comp)

        comp.handle_state(payload)

    def _handle_device_payload(self, payload):
        """Handle device payload."""
        device_id = payload["deviceId"]

        device = self._devices.get(device_id)

        if device is None:
            device = self._create_device_from_payload(payload)

            if device is None:
                return

            self._add_device(device)

        device.handle_state(payload)

    def _handle_room_payload(self, payload):
        """Handle room payload."""
        room_id = payload["roomId"]

        room = self._rooms.get(room_id)

        if room is None:
            room = self._create_room_from_payload(payload)

            if room is None:
                return

            self._add_room(room)

        room.handle_state(payload)

    def _handle_SET_ALL_DATA(self, payload):
        """Handle initial data setup."""
        if "lastItem" in payload:
            self.state = State.Ready
            self.on_initialized.set()
            _LOGGER.info("Bridge initialization complete - all data loaded")
            _LOGGER.info(
                "Loaded %d devices, %d components, %d rooms", len(self._devices), len(self._comps), len(self._rooms)
            )

        if "devices" in payload:
            _LOGGER.debug("Processing %d devices from SET_ALL_DATA", len(payload["devices"]))
            for device_payload in payload["devices"]:
                try:
                    self._handle_device_payload(device_payload)
                except (KeyError, ValueError):
                    _LOGGER.exception("Failed to handle device payload: %s", device_payload)

        if "comps" in payload:
            _LOGGER.debug("Processing %d components from SET_ALL_DATA", len(payload["comps"]))
            for comp_payload in payload["comps"]:
                try:
                    self._handle_comp_payload(comp_payload)
                except (KeyError, ValueError):
                    _LOGGER.exception("Failed to handle comp payload: %s", comp_payload)

        if "rooms" in payload:
            _LOGGER.debug("Processing %d rooms from SET_ALL_DATA", len(payload["rooms"]))
            for room_payload in payload["rooms"]:
                try:
                    self._handle_room_payload(room_payload)
                except (KeyError, ValueError):
                    _LOGGER.exception("Failed to handle room payload: %s", room_payload)

        if "roomHeating" in payload:
            _LOGGER.debug("Processing %d room heating configs from SET_ALL_DATA", len(payload["roomHeating"]))
            for room_payload in payload["roomHeating"]:
                try:
                    self._handle_room_payload(room_payload)
                except (KeyError, ValueError):
                    _LOGGER.exception("Failed to handle room heating payload: %s", room_payload)

    def _handle_SET_HOME_DATA(self, payload):
        """Handle home data updates."""
        # Store the full payload for reference
        self.home_data = payload

        # Extract bridge-specific information
        self.bridge_id = payload.get("id")
        self.bridge_name = payload.get("name")
        self.bridge_type = payload.get("bridgeType")

        # Extract home scenes count
        home_scenes = payload.get("homeScenes", [])
        self.home_scenes_count = len(home_scenes)

        _LOGGER.debug(
            "Bridge info updated: id=%s, name=%s, type=%s, fw=%s, scenes=%s",
            self.bridge_id,
            self.bridge_name,
            self.bridge_type,
            self.fw_version,
            self.home_scenes_count,
        )

    def _handle_SET_BRIDGE_STATE(self, payload):
        """Handle bridge state updates for sensors."""
        _LOGGER.debug(
            "Bridge %s (%s) state updated: %s",
            self.bridge_name or "Unknown",
            self.bridge_id or "Not initialized",
            payload,
        )

        # Only process if bridge is initialized
        if self.bridge_id is None:
            _LOGGER.warning(
                "Received bridge state update before bridge initialization complete - bridge_id not set yet"
            )
            return

        self.bridge_state.on_next(payload)

    def _handle_UNKNOWN(self, message_type, payload):
        """Handle unknown message types."""
        _LOGGER.warning("Unhandled message type [%s]: %s", message_type.name, payload)

    def _onMessage(self, message):
        """Handle incoming messages."""
        if "payload" in message:
            try:
                message_type = Messages(message["type_int"])
                method_name = "_handle_" + message_type.name
                _LOGGER.debug("Received message type: %s", message_type.name)
            except ValueError:
                # Unknown message type - log and skip
                _LOGGER.warning(
                    "Unknown message type: %s (payload: %s)", message.get("type_int"), message.get("payload")
                )
                return

            method = getattr(self, method_name, lambda p: self._handle_UNKNOWN(message_type, p))
            try:
                method(message["payload"])
            except (KeyError, ValueError):
                _LOGGER.exception("Error handling %s", method_name)
        else:
            _LOGGER.warning("Received message without payload: %s", message)

    async def _connect(self):
        """Establish connection to bridge."""
        _LOGGER.debug("Setting up secure connection to bridge")
        self.connection = await setup_secure_connection(self._session, self.ip_address, self.authkey)
        self.connection_subscription = self.connection.messages.subscribe(self._onMessage)

        # Extract firmware version from connection
        self.fw_version = self.connection.device_version
        _LOGGER.info("Secure connection established and message subscription active")
        _LOGGER.info("Bridge firmware version: %s", self.fw_version)

    async def close(self):
        """Close the bridge connection."""
        _LOGGER.info("Closing bridge connection")
        self.state = State.Closing
        self.on_initialized.clear()

        if isinstance(self.connection, SecureBridgeConnection):
            self.connection_subscription.dispose()
            await self.connection.close()
            _LOGGER.debug("Connection and subscription closed")

        if self._closeSession:
            await self._session.close()
            _LOGGER.debug("Session closed")

    async def wait_for_initialization(self):
        """Wait for bridge initialization to complete."""
        return await self.on_initialized.wait()

    async def get_comps(self):
        """Get all components."""
        await self.wait_for_initialization()

        _LOGGER.debug("Getting all components - total count: %d", len(self._comps))
        for comp_id, comp in self._comps.items():
            _LOGGER.debug("Component: id=%s, name=%s, type=%s", comp_id, comp.name, type(comp).__name__)

        return self._comps

    async def get_devices(self):
        """Get all devices."""
        await self.wait_for_initialization()

        _LOGGER.debug("Getting all devices - total count: %d", len(self._devices))
        for device_id, device in self._devices.items():
            _LOGGER.debug("Device: id=%s, name=%s, type=%s", device_id, device.name, type(device).__name__)

        return self._devices

    async def get_rooms(self):
        """Get all rooms."""
        await self.wait_for_initialization()

        _LOGGER.debug("Getting all rooms - total count: %d", len(self._rooms))
        for room_id, room in self._rooms.items():
            _LOGGER.debug("Room: id=%s, name=%s, type=%s", room_id, room.name, type(room).__name__)

        return self._rooms
