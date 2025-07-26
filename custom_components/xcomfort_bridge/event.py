"""Support for xComfort buttons."""

import logging

from xcomfort.devices import Rocker

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
                _LOGGER.debug("Adding %s", device)
                event = XComfortEvent(hass, hub, device)
                events.append(event)

        async_add_entities(events)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class XComfortEvent(EventEntity):
    """Entity class for xComfort event button."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Rocker) -> None:
        """Initialize the Event entity.

        Args:
            hass: HomeAssistant instance
            hub: XComfortHub instance
            device: Rocker device instance

        """
        self._attr_device_class = EventDeviceClass.BUTTON
        self._attr_event_types = ["on", "off"]
        self._attr_has_entity_name = True
        self._attr_name = device.name
        self._attr_unique_id = f"event_{DOMAIN}_{device.device_id}"
        self._device = device

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._device.state.subscribe(self._async_handle_event)

    @callback
    def _async_handle_event(self, state: bool) -> None:
        """Handle the button event."""

        if state is not None:
            self._trigger_event("on" if state else "off")
            self.async_write_ha_state()
