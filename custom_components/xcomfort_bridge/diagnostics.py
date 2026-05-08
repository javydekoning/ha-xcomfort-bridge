"""Diagnostics support for the Eaton xComfort Bridge integration.

Produces a redacted snapshot suitable for pasting into a bug report:
bridge metadata, discovered device/room/scene inventory with types and IDs,
and the current config entry (with secrets removed).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import XComfortHub

# Keys whose values must never leave the user's instance. IP address and
# bridge/hardware IDs are *not* redacted by default — they're what makes
# a bug report actionable, and the user is the one deciding to share.
_TO_REDACT = {
    "auth_key",
    "password",
    "pwd",
    "secret",
    "token",
}


def _raw_payload(obj: Any) -> dict[str, Any] | None:
    """Best-effort extraction of the latest raw payload for an object.

    Devices, rooms and components carry their most recent bridge payload
    either directly on `self.payload` (Rocker, Shade, door/window sensors)
    or inside the Rx state's `.raw` attribute (Light, Appliance, Heater,
    HeatingValve, RcTouch, Room). Comp caches both. Try both and return
    whichever is populated — or None if neither is.
    """
    state = getattr(obj, "state", None)
    if state is not None and hasattr(state, "value") and state.value is not None:
        raw = getattr(state.value, "raw", None)
        if isinstance(raw, dict):
            return raw
    payload = getattr(obj, "payload", None)
    if isinstance(payload, dict):
        return payload
    return None


def _summarise_device(device: Any) -> dict[str, Any]:
    """Collect a per-device description including the latest raw payload.

    The raw payload is what makes climate/heating/usage bugs diagnosable:
    it includes `usage`, `tempRoom`, `info[]`, `pidP/I/D`, `dimmable` etc.
    Secrets are stripped via the top-level redaction pass.
    """
    entry: dict[str, Any] = {
        "class": type(device).__name__,
        "device_id": getattr(device, "device_id", None),
        "name": getattr(device, "name", None),
        "comp_id": getattr(device, "comp_id", None),
        "dev_type": getattr(device, "dev_type", None),
    }
    state = getattr(device, "state", None)
    if state is not None and hasattr(state, "value"):
        entry["has_state"] = state.value is not None
    raw = _raw_payload(device)
    if raw is not None:
        entry["raw"] = raw
    return entry


def _summarise_comp(comp: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "comp_id": getattr(comp, "comp_id", None),
        "name": getattr(comp, "name", None),
        "comp_type": getattr(comp, "comp_type", None),
    }
    raw = _raw_payload(comp)
    if raw is not None:
        entry["raw"] = raw
    return entry


def _summarise_room(room: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "room_id": getattr(room, "room_id", None),
        "name": getattr(room, "name", None),
    }
    raw = _raw_payload(room)
    if raw is not None:
        entry["raw"] = raw
    return entry


def _summarise_scene(scene: Any) -> dict[str, Any]:
    return {
        "scene_id": getattr(scene, "scene_id", None),
        "name": getattr(scene, "name", None),
        "device_count": getattr(scene, "device_count", None),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry_snapshot = async_redact_data(
        {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        _TO_REDACT,
    )

    hub: XComfortHub | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if hub is None:
        return {
            "entry": entry_snapshot,
            "note": "Hub not loaded — integration may have failed to set up.",
        }

    bridge = hub.bridge
    bridge_info = {
        "bridge_id": hub.bridge.bridge_id,
        "bridge_name": hub.bridge.bridge_name,
        "bridge_type": hub.bridge.bridge_type,
        "bridge_model": hub.bridge_model,
        "firmware_version": hub.firmware_version,
        "state": getattr(bridge.state, "name", str(bridge.state)),
        "on_initialized": bridge.on_initialized.is_set(),
        "on_metadata_received": bridge.on_metadata_received.is_set(),
        "home_scene_ids": list(bridge.home_scene_ids),
        "scenes_count": bridge.scenes_count,
        "remote_allowed": bridge.remote_allowed.value,
        "remote_online": bridge.remote_online.value,
    }

    inventory = {
        "components": [_summarise_comp(c) for c in bridge.comps.values()],
        "devices": [_summarise_device(d) for d in bridge.devices.values()],
        "rooms": [_summarise_room(r) for r in bridge.rooms.values()],
        "scenes": [_summarise_scene(s) for s in bridge.scenes.values()],
    }

    return {
        "entry": entry_snapshot,
        "bridge": bridge_info,
        "counts": {
            "components": len(bridge.comps),
            "devices": len(bridge.devices),
            "rooms": len(bridge.rooms),
            "scenes": len(bridge.scenes),
        },
        "inventory": inventory,
    }
