# xcomfort-bridge-hass

Eaton xComfort integration with Home Assistant. Note that you need the **xComfort Bridge** for this to work.

## Device Compatibility

✅ for "Yes, "❌ for "No" or ⚠️ for "Partial" functionality.

| Device                          | Device Type | Tested | Functional |
|---------------------------------|-------------|--------|------------|
| Push Button 1-Fold              | CTAA-01/04  | ✅     | ✅        |
| Push Button 2-Fold              | CTAA-02/04  | ✅     | ✅        |
| Push Button 4-Fold              | CTAA-04/04  | ✅     | ✅        |
| Push Button MultiSensor 1-Fold  | CTSA-01/04  | ✅     | ✅        |
| Push Button MultiSensor 2-Fold  | CTSA-02/04  | ❌     |           |
| Push Button MultiSensor 4-Fold  | CTSA-04/04  | ❌     |           |
| Remote Control 2-Channel (mini) | CHSZ-02/02  | ✅     | ✅        |
| Room Control (Rc) Touch         | CRCA-00/08  | ✅     | ✅        |

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
2. Clone (your fork) of this repo. (e.g. `git clone git@github.com:javydekoning/ha-xcomfort-bridge.git -b dev`)
3. Open your IDE. Re-open in the `devcontainer`.
4. Run task "Run home assistant". Press `ctrl+shift+p` to open command pallet, `Tasks: Run task`, `Run Home Assistant`.
5. Optional, enable debug logging in `/workspaces/ha-xcomfort-bridge/config/configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.xcomfort_bridge: debug
    xcomfort: debug
```

6. Run the linter before opening PR!

```bash
uvx ruff check --config .github/linters/.ruff.toml --fix
```

## Using events in automations

This integration triggers events on button presses for push buttons, virtual Rc Touch buttons or remotes. There are 2 types:

- `press_up`
- `press_down`

The benefit of this is that you can map more devices than you could when you'd use them as "on/off". E.g. the below automation toggles a light, evertime a use presses up.

```yaml
alias: Toggle lamp with Remote
description: "Toggle living room lamp when remote button 1 (left) is pressed up."
triggers:
  - entity_id: event.remote_control_2_fold_button_1
    trigger: state
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.event_type == 'press_up' }}"
actions:
  - target:
      entity_id: light.my_light
    action: light.toggle
mode: single
```
