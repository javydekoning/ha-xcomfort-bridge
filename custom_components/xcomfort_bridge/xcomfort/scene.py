"""Scene model for xComfort integration."""

import logging

_LOGGER = logging.getLogger(__name__)


class Scene:
    """Scene representation."""

    def __init__(self, bridge, scene_id: int, name: str, payload: dict | None = None):
        """Initialize scene with bridge, ID, name and payload."""
        self.bridge = bridge
        self.scene_id = scene_id
        self.name = name
        self.payload = payload or {}

    def update(self, payload: dict) -> None:
        """Update scene payload."""
        if not payload:
            return
        self.payload.update(payload)
        if payload.get("name"):
            self.name = payload["name"]
        _LOGGER.debug("Updated scene %s (id: %s)", self.name, self.scene_id)

    @property
    def show(self) -> bool:
        """Return whether the scene is marked as visible."""
        return bool(self.payload.get("show", True))

    @property
    def order(self) -> int | None:
        """Return scene order."""
        return self.payload.get("order")

    @property
    def icon(self) -> str | None:
        """Return scene icon ID."""
        name = self.payload.get("name")

        icon_map = {
            "Home": "mdi:home-account",
            "Away": "mdi:home-off",
            "Night": "mdi:weather-night",
            "Morning": "mdi:weather-sunset-up",
        }

        return icon_map.get(name, "mdi:button-pointer")

    @property
    def devices(self) -> list:
        """Return scene devices list (deviceId, value, type)."""
        return self.payload.get("devices", [])

    @property
    def device_count(self) -> int:
        """Return number of devices in the scene."""
        return len(self.devices)

    async def activate(self) -> None:
        """Activate this scene."""
        await self.bridge.activate_scene(self.scene_id)

    def __str__(self):
        """Return string representation of scene."""
        return f'Scene({self.scene_id}, "{self.name}")'

    __repr__ = __str__
