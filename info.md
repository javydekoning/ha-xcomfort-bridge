# Configuration

Configuration for the Eaton xComfort bridge integration is done through the Home Assistant UI.

To add the integration, go to `Configuration->Integrations`, click `+` and search for `xcomfort`

To connect you need to fill in:
- IP Address: The IP address of your bridge.
- Auth Key: You find this on the backside of the bridge.
- Identifier: Lowercase nickname, will default to ip address if not supplied, i put in xcomfort.

# Stale heater readings

Some heater devices report power infrequently or without explicit "off" updates. If you experience stale power readings, consider using room-level power/energy sensors as the primary source of truth in automations and dashboards.
