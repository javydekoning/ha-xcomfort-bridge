"""Helpers for Home Assistant device registry metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .xcomfort.constants import ComponentTypes

if TYPE_CHECKING:
    from .hub import XComfortHub
    from .xcomfort.comp import Comp
    from .xcomfort.devices import HeatingValve, RcTouch


def _get_rctouch_component(hub: XComfortHub, device: RcTouch) -> Comp | None:
    """Return the linked xComfort component for an RcTouch device."""
    if device.comp_id is None:
        return None
    return hub.bridge.comps.get(device.comp_id)


def _get_rctouch_model_name(comp: Comp | None) -> str:
    """Return a human-readable RcTouch model name from discovery data."""
    if comp is not None and comp.comp_type == ComponentTypes.RC_TOUCH:
        return "RC Touch"
    return "RcTouch"


def get_rctouch_device_info(hub: XComfortHub, device: RcTouch) -> DeviceInfo:
    """Return stable device metadata for an RcTouch device.

    The identifier intentionally stays unchanged so existing Home Assistant
    device registry entries can be updated in place instead of creating a new
    device alongside the old unnamed one.
    """
    comp = _get_rctouch_component(hub, device)
    comp_payload = comp.payload if comp is not None else {}

    return DeviceInfo(
        identifiers={(DOMAIN, f"climate_{DOMAIN}_{hub.identifier}-{device.device_id}")},
        name=device.name
        or (comp.name if comp is not None else None)
        or f"RcTouch {device.device_id}",
        manufacturer="Eaton",
        model=_get_rctouch_model_name(comp),
        sw_version=comp_payload.get("versionFW"),
        hw_version=comp_payload.get("versionHW"),
        via_device=(DOMAIN, hub.hub_id),
    )


def get_heating_valve_device_info(hub: XComfortHub, device: HeatingValve) -> DeviceInfo:
    """Return stable device metadata for a HeatingValve device."""
    comp = hub.bridge.comps.get(device.comp_id) if device.comp_id is not None else None
    comp_payload = comp.payload if comp is not None else {}

    return DeviceInfo(
        identifiers={
            (DOMAIN, f"heating_valve_{DOMAIN}_{hub.identifier}-{device.device_id}")
        },
        name=device.name
        or (comp.name if comp is not None else None)
        or f"Heating Valve {device.device_id}",
        manufacturer="Eaton",
        model="Heating Valve CHVZ-01/05",
        sw_version=comp_payload.get("versionFW"),
        hw_version=comp_payload.get("versionHW"),
        via_device=(DOMAIN, hub.hub_id),
    )
