from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

device_module = load_module("device_module", ROOT / "device-service" / "app" / "main.py")
automation_module = load_module("automation_module", ROOT / "automation-service" / "app" / "main.py")
voice_module = load_module("voice_module", ROOT / "voice-service" / "app" / "main.py")
monitoring_module = load_module("monitoring_module", ROOT / "monitoring-service" / "app" / "main.py")
security_module = load_module("security_module", ROOT / "security-service" / "app" / "main.py")
integration_module = load_module("integration_module", ROOT / "integration-service" / "app" / "main.py")
notification_module = load_module("notification_module", ROOT / "notification-service" / "app" / "main.py")

device_client = TestClient(device_module.app)
automation_client = TestClient(automation_module.app)
voice_client = TestClient(voice_module.app)
monitoring_client = TestClient(monitoring_module.app)
security_client = TestClient(security_module.app)
integration_client = TestClient(integration_module.app)
notification_client = TestClient(notification_module.app)


def test_voice_to_device_command_pipeline() -> None:
    intent = voice_client.post(
        "/voice/parse",
        json={
            "text": "turn off living room light",
            "user_id": "USR-OWNER-1",
            "home_id": "HOME-DEMO",
            "provider": "dialogflow",
            "language": "ru",
        },
    )
    assert intent.status_code == 200
    payload = intent.json()
    assert payload["intent_type"] == "device_control"

    device = device_client.get("/devices/search", params={"name": "light", "home_id": "HOME-DEMO"})
    assert device.status_code == 200

    command = device_client.post(
        f"/devices/{device.json()['device_id']}/command",
        json={
            "action": "turn_off",
            "params": {},
            "source": "voice",
            "actor_id": "USR-OWNER-1",
            "actor_role": "owner",
        },
    )
    assert command.status_code == 200

    log = monitoring_client.post(
        "/monitoring/log-command",
        json={
            "event_id": str(uuid4()),
            "home_id": "HOME-DEMO",
            "user_id": "USR-OWNER-1",
            "device_id": device.json()["device_id"],
            "action": "turn_off",
            "source": "voice",
            "success": True,
            "latency_ms": command.json()["latency_ms"],
        },
    )
    assert log.status_code == 200


def test_security_and_scenario_flow() -> None:
    challenge = security_client.post(
        "/auth/challenge/start",
        json={"user_id": "USR-OWNER-1", "password": "owner123"},
    )
    assert challenge.status_code == 200

    verify = security_client.post(
        "/auth/challenge/verify",
        json={"challenge_id": challenge.json()["challenge_id"], "otp_code": "123456"},
    )
    assert verify.status_code == 200
    assert "access_token" in verify.json()

    activate = automation_client.post(
        "/scenarios/SCN-AWAY/activate",
        json={"actor_id": "USR-OWNER-1", "actor_role": "owner", "source": "automation"},
    )
    assert activate.status_code == 200
    assert activate.json()["planned_actions"] >= 1


def test_integrations_and_alerts_flow() -> None:
    connect = integration_client.post(
        "/integrations/smart-speaker/connect",
        json={
            "system_name": "smart_speaker",
            "payload": {"provider": "alisa"},
            "actor_id": "USR-ADMIN-1",
            "actor_role": "admin",
        },
    )
    assert connect.status_code == 200

    incident = notification_client.post(
        "/notify/incident",
        json={
            "home_id": "HOME-DEMO",
            "sensor": "smoke_sensor",
            "value": "triggered",
            "severity": "critical",
            "actor_role": "owner",
        },
    )
    assert incident.status_code == 200

    kpi = monitoring_client.get("/monitoring/kpi", params={"home_id": "HOME-DEMO"})
    assert kpi.status_code == 200
    assert "command_reaction_ms" in kpi.json()
