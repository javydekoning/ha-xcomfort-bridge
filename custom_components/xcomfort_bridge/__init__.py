"""Support for XComfort Bridge."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    AUTH_MODE_DEVICE,
    AUTH_MODE_USER,
    CONF_AUTH_KEY,
    CONF_AUTH_MODE,
    CONF_IDENTIFIER,
    CONF_USERNAME,
    DEFAULT_DEVICE_USERNAME,
    DOMAIN,
)
from .hub import XComfortHub
from .xcomfort.connection import InvalidAuth

# Bounded wait during entry setup — covers the handshake + first snapshot.
# Fifteen seconds is generous: a healthy bridge answers in <2 s. Anything
# slower is almost always a network or bridge problem, which we surface as
# ConfigEntryNotReady so HA retries with backoff.
_SETUP_TIMEOUT_S = 15.0

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.EVENT,
    Platform.SCENE,
]


_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Boilerplate."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connect to bridge and loads devices."""
    config = entry.data
    identifier = str(config.get(CONF_IDENTIFIER))
    ip = str(config.get(CONF_IP_ADDRESS))
    auth_key = str(config.get(CONF_AUTH_KEY))

    # Entries created before user-auth support lack CONF_AUTH_MODE; treat
    # them as the legacy device-code flow (username "default"). When present,
    # AUTH_MODE_USER uses the user-chosen name; AUTH_MODE_DEVICE is explicit
    # and still uses "default" on the wire.
    auth_mode = config.get(CONF_AUTH_MODE, AUTH_MODE_DEVICE)
    if auth_mode == AUTH_MODE_USER:
        username = str(config.get(CONF_USERNAME) or DEFAULT_DEVICE_USERNAME)
    else:
        username = DEFAULT_DEVICE_USERNAME

    hub = XComfortHub(
        hass,
        identifier=identifier,
        ip=ip,
        auth_key=auth_key,
        entry=entry,
        username=username,
    )
    hass.data[DOMAIN][entry.entry_id] = hub

    # Start the bridge connection as a background task. Its lifecycle is
    # independent of setup — setup just needs to know the bridge reached a
    # usable state (or failed) before returning.
    run_task = entry.async_create_background_task(
        hass, hub.bridge.run(), f"XComfort/{identifier}"
    )

    # Wait for either the bridge to report ready or run() to fail. Racing
    # the two lets us surface an auth rejection as a typed HA exception
    # instead of hanging on the init event forever.
    init_waiter = asyncio.create_task(hub.bridge.wait_for_initialization())
    metadata_waiter = asyncio.create_task(hub.bridge.on_metadata_received.wait())
    try:
        done, pending = await asyncio.wait(
            {init_waiter, metadata_waiter, run_task},
            timeout=_SETUP_TIMEOUT_S,
            return_when=asyncio.FIRST_COMPLETED,
        )
    except BaseException:
        init_waiter.cancel()
        metadata_waiter.cancel()
        raise

    # If run_task finished, something went wrong — it should normally run
    # for the lifetime of the entry. An InvalidAuth maps to an HA reauth
    # prompt; anything else to a transient-not-ready.
    if run_task in done:
        init_waiter.cancel()
        metadata_waiter.cancel()
        exc = run_task.exception()
        if isinstance(exc, InvalidAuth):
            raise ConfigEntryAuthFailed("Bridge rejected auth key") from exc
        raise ConfigEntryNotReady(
            f"Bridge run loop stopped during setup: {exc!r}"
        ) from exc

    # Ready path: init event fired. Give SET_BRIDGE_DATA a brief head start
    # so bridge metadata is populated before we register the HA device. The
    # metadata waiter is already running; it typically completes within a
    # few hundred ms of init. If it doesn't, we proceed with whatever we
    # have — the device registry entry will be updated later when the
    # metadata eventually arrives.
    if not init_waiter.done():
        init_waiter.cancel()
    if not metadata_waiter.done():
        try:
            await asyncio.wait_for(
                asyncio.shield(hub.bridge.on_metadata_received.wait()), timeout=2.0
            )
        except TimeoutError:
            _LOGGER.debug(
                "Bridge metadata (SET_BRIDGE_DATA) not received within 2s; "
                "continuing setup, will update device registry when it arrives"
            )

    # Pending must still be awaited/cancelled so we don't leak tasks.
    for task in pending:
        if task is run_task:
            continue  # keep the long-lived run loop going
        task.cancel()

    # If timeout elapsed with neither event nor failure, the bridge is
    # unreachable or stalled — HA should retry setup with backoff.
    if not hub.bridge.on_initialized.is_set():
        raise ConfigEntryNotReady(
            f"Bridge at {ip} did not become ready within {_SETUP_TIMEOUT_S:.0f}s"
        )

    _LOGGER.info(
        "Hub info - ID: %s, Name: %s, Model: %s, FW: %s",
        hub.hub_id,
        hub.bridge_name,
        hub.bridge_model,
        hub.firmware_version,
    )

    # Register the device with all hub information
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, hub.hub_id)},
        manufacturer="Eaton",
        name=hub.bridge_name or entry.title,
        model=hub.bridge_model,
        sw_version=hub.firmware_version,
        serial_number=hub.bridge.bridge_id,
    )

    # Update device info in case it already existed
    device_registry.async_update_device(
        device.id,
        name=hub.bridge_name or entry.title,
        model=hub.bridge_model,
        sw_version=hub.firmware_version,
        serial_number=hub.bridge.bridge_id,
    )

    entry.async_create_task(hass, hub.load_devices())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Disconnects from bridge and removes devices loaded."""
    hub = XComfortHub.get_hub(hass, entry)
    await hub.stop()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
