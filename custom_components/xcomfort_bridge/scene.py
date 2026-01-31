"""Support for xComfort scenes."""

import logging

try:
    # HA <= 2025.x
    from homeassistant.components.scene import SceneEntity as HA_SceneEntity
except ImportError:  # HA >= 2026.x
    from homeassistant.components.scene import Scene as HA_SceneEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub
from .xcomfort.scene import Scene as XComfortScene

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up xComfort scenes."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        scenes = list(getattr(hub, "scenes", []))
        _LOGGER.debug("Found %s xcomfort scenes", len(scenes))

        entities = [HASSXComfortScene(hub, scene) for scene in scenes]

        _LOGGER.debug("Added %s scenes", len(entities))
        async_add_entities(entities)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class HASSXComfortScene(HA_SceneEntity):
    """Entity class for xComfort scenes."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hub: XComfortHub, scene: XComfortScene):
        """Initialize the scene entity."""
        self.hub = hub
        self._scene = scene
        self._attr_name = scene.name
        self._attr_unique_id = f"scene_{DOMAIN}_{hub.identifier}-{scene.scene_id}"

        bridge_name = hub.bridge_name or hub.identifier
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.hub_id}_scenes")},
            name=f"{bridge_name} Scenes",
            manufacturer="Eaton",
            model="xComfort Scenes",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, hub.hub_id),
        )

    async def async_activate(self, **kwargs) -> None:
        """Activate the scene."""
        _LOGGER.debug("Activating scene %s (id=%s)", self._scene.name, self._scene.scene_id)
        await self._scene.activate()

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return {
            "scene_id": self._scene.scene_id,
            "order": self._scene.order,
            "show": self._scene.show,
            "icon": self._scene.icon,
            "device_count": self._scene.device_count,
            "home_scene": self._scene.scene_id in self.hub.bridge.home_scene_ids,
        }
