"""Support for xComfort buttons."""

import logging

from xcomfort.comp import Comp
from xcomfort.devices import Light, Rocker, Shade

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up xComfort event devices."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        events = []
        for device in hub.devices:
            if isinstance(device, Rocker):
                comp = device.bridge._comps.get(device.payload.get("compId", ""))
                _LOGGER.debug("Adding %s %s", device, comp)
                event = XComfortEvent(hass, hub, device, comp)
                events.append(event)

        async_add_entities(events)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class XComfortEvent(EventEntity):
    """Entity class for xComfort event button."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Rocker, comp: Comp) -> None:
        """Initialize the Event entity.

        Args:
            hass: HomeAssistant instance
            hub: XComfortHub instance
            device: Rocker device instance
            comp: XComfort Comp instance

        """
        self._attr_device_class = EventDeviceClass.BUTTON
        # For multisensor rockers (momentary), use press_up/press_down
        # For regular rockers (toggle), use on/off
        if device.has_sensors:
            self._attr_event_types = ["press_up", "press_down"]
            self._is_momentary = True
        else:
            self._attr_event_types = ["on", "off"]
            self._is_momentary = False

        self._attr_has_entity_name = True
        self._attr_name = f"{comp.name} {device.name}"
        self._attr_unique_id = f"event_{DOMAIN}_{device.device_id}"
        self._device = device

        control_ids = device.payload.get("controlId", [])
        device_info_set = False

        if len(control_ids) == 1:
            # exhactly one controlled device, will add it to the same HASS-device

            # ignore private-member-access because library miss a non-async way to get devices
            # ruff: noqa: SLF001
            controlled_device = device.bridge._devices.get(control_ids[0])
            if controlled_device is not None:
                controlled_device_id = None
                if isinstance(controlled_device, Light):
                    controlled_device_id = f"light_{DOMAIN}_{hub.identifier}-{controlled_device.device_id}"

                if isinstance(controlled_device, Shade):
                    controlled_device_id = f"shade_{DOMAIN}_{hub.identifier}-{controlled_device.device_id}"

                if controlled_device_id is not None:
                    self._attr_device_info = DeviceInfo(
                        identifiers={(DOMAIN, controlled_device_id)},
                    )
                    device_info_set = True

        # If device_info wasn't set and this is a multisensor rocker,
        # create a dedicated device for it so sensors can be grouped
        if not device_info_set and self._is_momentary:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"event_{DOMAIN}_{device.device_id}")},
                name=comp.name,
                manufacturer="Eaton",
                model="Pushbutton Multisensor 1-fold",
            )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._device.state.subscribe(self._async_handle_event)

    @callback
    def _async_handle_event(self, state) -> None:
        """Handle the button event."""

        if state is None:
            return

        # For momentary rockers, extract the actual button state
        if self._is_momentary:
            # state is RockerSensorState or bool
            if hasattr(state, 'is_on'):
                button_state = state.is_on
            else:
                button_state = bool(state)

            # Emit press_up or press_down events
            self._trigger_event("press_up" if button_state else "press_down")
        else:
            # For toggle rockers, use on/off events
            self._trigger_event("on" if state else "off")

        self.async_write_ha_state()
