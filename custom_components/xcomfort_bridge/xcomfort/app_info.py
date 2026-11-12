"""Human-readable messages for APP_INFO (msg 295) payloads.

The bridge pushes APP_INFO in response to user-initiated commands (deleting
a scene that no longer exists, activating a dimmer on a non-dimmable device,
etc.). The payload shape is `{"info": "<code>", "value"?: ..., ...}` where
<code> is a 4-digit i18n key from the official app's `en.json`.

Mapping + substitution logic mirrors the app's `getAppInfo` function
(see reverse-engineering notes in CLAUDE.md). The strings here are
paraphrased from en.json to read naturally in logs — the code is kept
verbatim so the original can always be looked up.
"""

from __future__ import annotations

# Keys are the 4-digit codes delivered in payload["info"]. Placeholders use
# {value} / {value1} / {value2} / {type} and are substituted from the
# remaining top-level fields in the payload.
APP_INFO_MESSAGES: dict[str, str] = {
    "1000": "Bad device type",
    "1001": "Device already exists",
    "1002": "Unknown device",
    "1003": "Unknown room",
    "1004": "Failed creating room",
    "1005": "Failed creating device",
    "1006": "Failed creating scene",
    "1007": "No device/room/scene with this ID",
    "1008": "Unknown scene",
    "1009": "Room not dimmable",
    "1010": "Device not dimmable",
    "1011": "Learning mode started",
    "1012": "Learning mode ended",
    "1013": "Infinite toggle (dev: {value}) start",
    "1014": "Infinite toggle end",
    "1015": "Invalid action",
    "1016": "Barcode scan data invalid",
    "1017": "Failed updating room (ID: {value})",
    "1018": "Failed updating scene (ID: {value})",
    "1019": "Not allowed while learning mode is active",
    "1020": "A dimming actuator has been found",
    "1021": "A switching actuator has been found",
    "1022": "Device removed: protected by a different password",
    "1023": "Device (serial {value}) removed: unsupported device type",
    "1024": "Failed creating timer",
    "1025": "Failed updating timer (ID: {value})",
    "1026": "No room/scene with this control ID",
    "1027": "Unknown timer",
    "1028": "Sensor protected by an unknown password",
    "1029": "Device (ID: {value}) removed: unknown password",
    "1030": "Device (ID: {value}) removed: unsupported device type",
    "1031": "Unknown device",
    "1032": "Failed creating device",
    "1033": "New component added to bridge (serial {value})",
    "1034": "Operate device (serial {value}) to finalize configuration",
    "1035": "Mode not editable: device already in use",
    "1036": "Device (ID: {value}) was removed after mode update",
    "1037": "Device(s) skipped due to sensor overflow",
    "1038": "Failed creating heating program",
    "1039": "Failed updating heating program (ID: {value})",
    "1040": "Unknown heating program",
    "1041": "Failed creating climate zone",
    "1042": "Failed updating climate zone (ID: {value})",
    "1043": "Unknown climate zone",
    "1044": "Not configured",
    "1045": "Effect regulation requires all heating actuators at firmware > V1.50",
    "1046": "No floor sensor at room control",
    "1047": "No room sensor defined",
    "1048": "No floor sensor defined",
    "1049": "SupportID: {value}",
    "1050": "RCT may have old firmware",
    "1051": "RCT needs new firmware",
    "1052": "Server communication error ({value})",
    "1053": "Data reception error (not prepared)",
    "1054": "Data reception error (no data)",
    "1055": "Data reception error (data overflow)",
    "1056": "Backup restore error",
    "1057": "Backup could not be saved on server ({value})",
    "1058": "Authentication failed",
    "1059": "A shading actuator has been found",
    "1060": "A water-safety device has been found",
    "1061": "Water sensor cannot be assigned: max assignments reached",
    "1062": "Yale-Integration communication error",
    "1063": "Unknown user",
    "1064": "Failed creating user",
    "1065": "Username already used by another user",
    "1066": "Email address already used by another user",
    "1067": "Advanced Regulation not possible (missing heating actuators at V1.53+)",
    "1068": "Multi-Heating Actuator valves in zone have mismatched usage",
    "1069": "Climate devices with cooling require Advanced Regulation",
    "1070": "Heating actuators below V1.53 don't support Advanced Regulation",
    "1071": "Climate devices don't support Advanced Regulation",
    "1072": "Climate regulation with switching/dimming actuator requires Advanced Regulation",
    "1073": "Failed creating time program",
    "1074": "Failed updating time program",
    "1075": "Unknown time program",
    "1076": "Unknown condition",
    "1077": "Failed creating condition",
    "1078": "Failed creating push note",
    "1079": "Unknown push note",
    "1080": "Failed to create client-bridge",
    "1081": "Unknown client-bridge",
    "1082": "Master-client not allowed (already in use)",
    "1083": "Failed to create meter",
    "1084": "Unknown meter",
    "1085": "History request currently not possible",
}


def format_app_info(payload: dict) -> tuple[str, str]:
    """Resolve an APP_INFO payload to (code, human-readable message).

    Returns the code as a string (for use as a log tag) and a formatted
    message. Unknown codes produce a fallback message that includes the
    full payload so they can be identified and added to the table.
    """
    code = str(payload.get("info", ""))
    template = APP_INFO_MESSAGES.get(code)
    if template is None:
        return code, f"unmapped code {code}: {payload}"
    try:
        return code, template.format(**payload)
    except (KeyError, IndexError):
        # Placeholder expected but not supplied — fall back to raw template.
        return code, template
