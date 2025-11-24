"""Support for xComfort buttons."""

import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub
from .xcomfort.comp import Comp
from .xcomfort.constants import ComponentTypes
from .xcomfort.devices import RcTouch, Rocker

_LOGGER = logging.getLogger(__name__)

# Mapping of component types to their model names
COMPONENT_TYPE_TO_MODEL = {
    ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_1_CHANNEL: "1-Channel Pushbutton Multi Sensor",
    ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_2_CHANNEL: "2-Channel Pushbutton Multi Sensor",
    ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_4_CHANNEL: "4-Channel Pushbutton Multi Sensor",
    ComponentTypes.PUSH_BUTTON_1_CHANNEL: "1-Channel Pushbutton",
    ComponentTypes.PUSH_BUTTON_2_CHANNEL: "2-Channel Pushbutton",
    ComponentTypes.PUSH_BUTTON_4_CHANNEL: "4-Channel Pushbutton",
    ComponentTypes.REMOTE_CONTROL_2_CHANNEL: "2-Channel Remote Control",
    ComponentTypes.RC_TOUCH: "RC Touch",
}

# Multi-channel component types that should be grouped into a single device
MULTI_CHANNEL_COMPONENTS = {
    ComponentTypes.PUSH_BUTTON_2_CHANNEL: 2,
    ComponentTypes.PUSH_BUTTON_4_CHANNEL: 4,
    ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_2_CHANNEL: 2,
    ComponentTypes.PUSH_BUTTON_MULTI_SENSOR_4_CHANNEL: 4,
    ComponentTypes.REMOTE_CONTROL_2_CHANNEL: 2,
}


def _is_multi_channel_component(comp_type: int) -> bool:
    """Check if a component type is multi-channel."""
    return comp_type in MULTI_CHANNEL_COMPONENTS


def _get_channel_count(comp_type: int) -> int:
    """Get the number of channels for a multi-channel component."""
    return MULTI_CHANNEL_COMPONENTS.get(comp_type, 1)


def _is_momentary_rocker(comp: Comp) -> bool:
    """Check if a rocker component is a momentary pushbutton (neutral position).

    Args:
        comp: XComfort Comp instance

    Returns:
        True if the rocker is a pushbutton type.
        For now always returns True. Don't have full coverage of all types.

    """
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up xComfort event devices."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        events = []

        # Loop through components (xComfort components = HA devices)
        for comp in hub.bridge.comps.values():
            # Check if this is a pushbutton or remote control component type
            if comp.comp_type not in COMPONENT_TYPE_TO_MODEL:
                continue

            _LOGGER.debug(
                "Processing component %s (id: %s, type: %s)",
                comp.name,
                comp.comp_id,
                comp.comp_type,
            )

            # Find all devices (rockers) that belong to this component
            component_devices = [
                device
                for device in hub.devices
                if isinstance(device, Rocker) and hasattr(device, "comp_id") and device.comp_id == comp.comp_id
            ]

            if not component_devices:
                _LOGGER.warning("Component %s (type: %s) has no rocker devices, skipping", comp.name, comp.comp_type)
                continue

            # Sort by device_id to ensure consistent ordering
            component_devices.sort(key=lambda d: d.device_id)

            _LOGGER.debug(
                "Component %s has %d rocker device(s): %s",
                comp.name,
                len(component_devices),
                [d.name for d in component_devices],
            )

            # Check if this is a multi-channel component
            if _is_multi_channel_component(comp.comp_type):
                # Create an event entity for each rocker device in this component
                for idx, rocker in enumerate(component_devices):
                    button_number = idx + 1
                    _LOGGER.debug(
                        "Adding rocker %s as button %d of multi-channel component %s",
                        rocker.name,
                        button_number,
                        comp.name,
                    )
                    event = XComfortEvent(hass, hub, rocker, comp, button_number=button_number)
                    events.append(event)
            else:
                # Single channel device
                for rocker in component_devices:
                    _LOGGER.debug(
                        "Adding rocker %s for single-channel component %s (comp_type: %s, has_sensors: %s)",
                        rocker.name,
                        comp.name,
                        comp.comp_type,
                        rocker.has_sensors,
                    )
                    event = XComfortEvent(hass, hub, rocker, comp)
                    events.append(event)

        # Handle RcTouch devices separately
        for device in hub.devices:
            if isinstance(device, RcTouch):
                comp = device.bridge.comps.get(device.comp_id)
                _LOGGER.debug(
                    "Adding RcTouch button events for %s (comp: %s, comp_type: %s)",
                    device.name,
                    comp.name if comp else "Unknown",
                    comp.comp_type if comp else None,
                )
                event = XComfortRcTouchEvent(hass, hub, device, comp)
                events.append(event)

        async_add_entities(events)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class XComfortEvent(EventEntity):
    """Entity class for xComfort event button."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub: XComfortHub,
        device: Rocker,
        comp: Comp,
        button_number: int | None = None,
    ) -> None:
        """Initialize the Event entity.

        Args:
            hass: HomeAssistant instance
            hub: XComfortHub instance
            device: Rocker device instance (xComfort device = HA entity)
            comp: XComfort Comp instance (xComfort component = HA device)
            button_number: Button number for multi-channel devices (1-based)

        """
        self._attr_device_class = EventDeviceClass.BUTTON
        # Check if rocker is momentary (has neutral position)
        # This includes multisensor rockers and regular rockers configured as momentary
        self._is_momentary = device.has_sensors or _is_momentary_rocker(comp)

        if self._is_momentary:
            self._attr_event_types = ["press_up", "press_down"]
        else:
            self._attr_event_types = ["on", "off"]

        self._attr_has_entity_name = True
        self._button_number = button_number
        self._comp = comp

        # Set entity name based on whether it's a multi-channel device
        if button_number is not None:
            self._attr_name = f"Button {button_number}"
        else:
            # For single-channel, use just the device name since the component name is the device name
            self._attr_name = device.name

        self._attr_unique_id = f"event_{DOMAIN}_{device.device_id}"
        self._device = device
        self._has_initialized = False

        # xComfort Component = Home Assistant Device
        # Always create/reference a device based on the component
        model = COMPONENT_TYPE_TO_MODEL.get(comp.comp_type, "Unknown")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"event_{DOMAIN}_comp_{comp.comp_id}")},
            name=comp.name,
            manufacturer="Eaton",
            model=model,
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._device.state.subscribe(self._async_handle_event)

    @callback
    def _async_handle_event(self, state) -> None:
        """Handle the button event."""

        if state is None:
            return

        # Skip the very first state after HA restart
        if not self._has_initialized:
            self._has_initialized = True
            return

        # For momentary rockers, extract the actual button state
        if self._is_momentary:
            # state is RockerSensorState or bool
            if hasattr(state, "is_on"):
                button_state = state.is_on
            else:
                button_state = bool(state)

            # Emit press_up or press_down events
            self._trigger_event("press_up" if button_state else "press_down")
        else:
            # For toggle rockers, use on/off events
            self._trigger_event("on" if state else "off")

        self.async_write_ha_state()


class XComfortRcTouchEvent(EventEntity):
    """Entity class for xComfort RcTouch button events."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: RcTouch, comp: Comp) -> None:
        """Initialize the RcTouch Event entity.

        Args:
            hass: HomeAssistant instance
            hub: XComfortHub instance
            device: RcTouch device instance
            comp: XComfort Comp instance

        """
        self._attr_device_class = EventDeviceClass.BUTTON
        # RcTouch buttons are momentary (press up/down)
        self._attr_event_types = ["press_up", "press_down"]
        self._attr_has_entity_name = True
        self._attr_name = "Button"
        self._attr_unique_id = f"event_{DOMAIN}_{device.device_id}"
        self._device = device

        # Link to the RcTouch climate device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"climate_{DOMAIN}_{hub.identifier}-{device.device_id}")},
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Subscribe to button_state instead of regular state
        self._device.button_state.subscribe(self._async_handle_event)

    @callback
    def _async_handle_event(self, state) -> None:
        """Handle the button event."""
        if state is None:
            return

        # state is bool (True = pressed/up, False = released/down)
        button_state = bool(state)

        # Emit press_up or press_down events
        self._trigger_event("press_up" if button_state else "press_down")
        self.async_write_ha_state()
