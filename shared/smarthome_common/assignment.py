from __future__ import annotations

from collections import Counter

from .schemas import IntentType


def parse_voice_command_text(text: str) -> dict[str, object]:
    normalized = text.lower().strip()
    if not normalized:
        return {"intent_type": IntentType.UNKNOWN.value, "device_name": None, "action": None, "confidence": 0.0}

    action_map = {
        "turn_on": ["turn on", "enable", "switch on", "включ"],
        "turn_off": ["turn off", "disable", "switch off", "выключ"],
        "lock": ["lock", "закрой"],
        "unlock": ["unlock", "открой"],
        "set_temperature": ["temperature", "temp", "градус"],
        "set_brightness": ["brightness", "ярк"],
        "set_volume": ["volume", "громк"],
    }
    devices = ["light", "lamp", "tv", "speaker", "thermostat", "door", "camera", "socket", "ламп", "двер"]

    detected_action = None
    for action, tokens in action_map.items():
        if any(token in normalized for token in tokens):
            detected_action = action
            break

    detected_device = None
    for token in devices:
        if token in normalized:
            detected_device = token
            break

    if "scenario" in normalized or "scene" in normalized or "сценар" in normalized:
        return {
            "intent_type": IntentType.SCENARIO_ACTIVATE.value,
            "device_name": None,
            "action": "activate_scenario",
            "confidence": 0.91,
        }

    if detected_action and detected_device:
        return {
            "intent_type": IntentType.DEVICE_CONTROL.value,
            "device_name": detected_device,
            "action": detected_action,
            "confidence": 0.96,
        }

    if detected_device:
        return {
            "intent_type": IntentType.STATUS_QUERY.value,
            "device_name": detected_device,
            "action": "status",
            "confidence": 0.83,
        }

    return {
        "intent_type": IntentType.UNKNOWN.value,
        "device_name": None,
        "action": None,
        "confidence": 0.35,
    }


def recommend_behavior_scenarios(command_history: list[dict[str, str]]) -> list[str]:
    if not command_history:
        return []
    sequence = [f"{item.get('room', 'unknown')}:{item.get('action', 'unknown')}" for item in command_history]
    top = Counter(sequence).most_common(3)
    recommendations = []
    for item, _ in top:
        room, action = item.split(":", maxsplit=1)
        recommendations.append(f"auto_{room}_{action}")
    return recommendations


def suggest_energy_saving_actions(samples: list[float]) -> list[str]:
    if not samples:
        return []
    average = sum(samples) / len(samples)
    actions: list[str] = []
    if average > 900:
        actions.append("Enable eco mode for HVAC devices.")
    if max(samples) > 1200:
        actions.append("Schedule heavy appliances for off-peak hours.")
    if average > 500:
        actions.append("Lower default lighting brightness at night.")
    return actions
