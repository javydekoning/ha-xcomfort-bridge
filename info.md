# Configuration

Configuration for the Eaton xComfort bridge integration is done through the Home Assistant UI.

To add the integration, go to `Configuration->Integrations`, click `+` and search for `xcomfort`

To connect you need to fill in:
- IP Address: The IP address of your bridge.
- Auth Key: You find this on the backside of the bridge.
- Identifier: Lowercase nickname, will default to ip address if not supplied, i put in xcomfort.

# Heater power stale protection (experimental)

This option is intended to reduce over-reported heater power when heater devices send stale or incomplete payloads.

How it works:
- If a matched room reports power at or below 0.5 W for 20 seconds, the heater power sensor is forced to 0 W.
- A periodic check runs every 20 seconds to catch stale heaters even without new room updates.
- The same fallback is applied when calculating heater energy.
When the fallback is triggered, a warning is logged so you can see when stale protection was applied.
Heater-to-room mapping is name-based. We normalize names to lowercase and strip common prefixes like "varmekabel", "panelovn", and "heater", then look for an exact match. If none is found, we try prefix matches (either direction) and use the first match.
When stale protection is enabled, the mapping results are logged at INFO level at startup/reload so you can verify which heaters map to which rooms.

Why it exists:
- Some heater devices rarely send explicit "off" updates.
- Room power is often more reliable, so it is used as a safety fallback.

Warnings and limitations:
- Experimental and lightly tested. It may under-report real power if room power is delayed or missing.
- Not tested in rooms with multiple heaters.
- The heater-to-room match is name-based. If names do not align, the fallback will not activate.
