from shared.smarthome_common import (
    parse_voice_command_text,
    recommend_behavior_scenarios,
    suggest_energy_saving_actions,
)


def test_parse_voice_command() -> None:
    parsed = parse_voice_command_text("turn off living room light")
    assert parsed["intent_type"] == "device_control"
    assert parsed["action"] == "turn_off"


def test_behavior_recommendations() -> None:
    recs = recommend_behavior_scenarios(
        [
            {"room": "living_room", "action": "off"},
            {"room": "living_room", "action": "off"},
            {"room": "hall", "action": "set_temperature"},
        ]
    )
    assert recs
    assert recs[0].startswith("auto_")


def test_energy_saving_suggestions() -> None:
    actions = suggest_energy_saving_actions([420, 980, 1250, 870])
    assert actions
