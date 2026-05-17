from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.smarthome_common import NotificationChannel, NotificationRequest, Role, Settings, Severity, has_permission

settings = Settings(service_name="notification-service", service_port=8506)
app = FastAPI(title="SmartHome Notification Service", version="1.0.0")

messages: list[dict[str, Any]] = []


class IncidentAlertRequest(BaseModel):
    home_id: str
    sensor: str
    value: str
    severity: Severity = Severity.CRITICAL
    actor_role: Role


IncidentAlertRequest.model_rebuild()


def _assert_send(role: Role) -> None:
    if not has_permission(role, "notification:send") and role != Role.OWNER:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send(request: NotificationRequest) -> dict[str, Any]:
    _assert_send(request.actor_role)
    payload = request.model_dump(mode="json")
    payload["status"] = "queued"
    messages.append(payload)
    return payload


@app.post("/notify/incident")
async def incident(request: IncidentAlertRequest) -> dict[str, Any]:
    _assert_send(request.actor_role)
    payload = {
        "channel": NotificationChannel.PUSH.value,
        "recipient": request.home_id,
        "subject": f"Incident: {request.sensor}",
        "body": f"Sensor {request.sensor} reported value {request.value}",
        "severity": request.severity.value,
        "status": "queued",
    }
    messages.append(payload)
    return payload


@app.post("/notify/voice")
async def voice_notice(home_id: str, text: str, actor_role: Role = Role.OWNER) -> dict[str, Any]:
    _assert_send(actor_role)
    payload = {
        "channel": NotificationChannel.VOICE.value,
        "recipient": home_id,
        "subject": "Voice notification",
        "body": text,
        "severity": Severity.INFO.value,
        "status": "queued",
    }
    messages.append(payload)
    return payload


@app.get("/notify/history")
async def history(limit: int = 100) -> dict[str, Any]:
    return {"items": messages[-limit:], "count": len(messages)}