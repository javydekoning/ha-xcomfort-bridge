# xcomfort-bridge-hass

Eaton xComfort integration with Home Assistant. Note that you need the **xComfort Bridge** for this to work.

Developers, if you want to debug this, look at the [instructions found here](Debug.md)

## Installation

From HACS

1. Add repository `javydekoning/ha-xcomfort-bridge`
2. Set type to _Integration_
3. Download the newly added integration.
4. Restart Home Assistant
5. Go to _Settings -> Devices & Services -> Add integration -> Eaton xComfort Bridge_

## Credits

This repo is a (detached) fork of [jankrib/ha-xcomfort-bridge](https://github.com/jankrib/ha-xcomfort-bridge).

## Contributing & development.

1. Create a parent dir (e.g. `~/xcomfort`)
2. Clone (your fork) of this repo.
3. Clone `https://github.com/javydekoning/xcomfort-python`.
4. Open your IDE in the `devcontainer`. Run task "Run home assistant"
5. Optional, enable debug logging in `/workspaces/ha-xcomfort-bridge/config/configuration.yaml`:

    ```yaml
    logger:
    default: warning
    logs:
        custom_components.xcomfort_bridge: debug
        xcomfort: debug
    ```
