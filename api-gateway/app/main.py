from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.smarthome_common import (
    CommandSource,
    NotificationChannel,
    ProcessCommandWorkflowResult,
    Role,
    Settings,
    Severity,
    TwoFactorStartRequest,
    TwoFactorVerifyRequest,
    VoiceProvider,
    verify_token,
)


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8500

    device_service_url: str = "http://device-service:8501"
    automation_service_url: str = "http://automation-service:8502"
    voice_service_url: str = "http://voice-service:8503"
    monitoring_service_url: str = "http://monitoring-service:8504"
    security_service_url: str = "http://security-service:8505"
    notification_service_url: str = "http://notification-service:8506"
    integration_service_url: str = "http://integration-service:8507"

    jwt_secret: str = Settings().jwt_secret

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="SmartHome Hub API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5178",
        "http://127.0.0.1:5178",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessCommandRequest(BaseModel):
    user_id: str
    home_id: str = "HOME-DEMO"
    source: CommandSource = CommandSource.UI
    command_text: str | None = None
    device_id: str | None = None
    device_name: str | None = None
    action: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    actor_role: Role = Role.OWNER


class RunScenarioRequest(BaseModel):
    user_id: str
    home_id: str = "HOME-DEMO"
    scenario_id: str
    actor_role: Role = Role.OWNER


class VerifyAuthRequest(BaseModel):
    token: str


ProcessCommandRequest.model_rebuild()
RunScenarioRequest.model_rebuild()
VerifyAuthRequest.model_rebuild()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "device": settings.device_service_url,
        "automation": settings.automation_service_url,
        "voice": settings.voice_service_url,
        "monitoring": settings.monitoring_service_url,
        "security": settings.security_service_url,
        "notification": settings.notification_service_url,
        "integration": settings.integration_service_url,
    }


async def _resolve_device(
    client: httpx.AsyncClient,
    home_id: str,
    device_id: str | None,
    device_name: str | None,
) -> dict[str, Any]:
    if device_id:
        return await _get_json(client, f"{settings.device_service_url}/devices/{device_id}")
    if device_name:
        return await _get_json(
            client,
            f"{settings.device_service_url}/devices/search",
            {"name": device_name, "home_id": home_id},
        )
    raise HTTPException(status_code=400, detail="device_id or device_name is required")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/services/health")
async def service_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except HTTPException as exc:
                statuses[name] = {"status": "error", "detail": exc.detail}
            except httpx.HTTPError as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/auth/challenge/start")
async def auth_start(request: TwoFactorStartRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await _post_json(
            client,
            f"{settings.security_service_url}/auth/challenge/start",
            request.model_dump(mode="json"),
        )


@app.post("/auth/challenge/verify")
async def auth_verify(request: TwoFactorVerifyRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await _post_json(
            client,
            f"{settings.security_service_url}/auth/challenge/verify",
            request.model_dump(mode="json"),
        )


@app.post("/auth/verify")
async def verify_auth(request: VerifyAuthRequest) -> dict[str, Any]:
    payload = verify_token(request.token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.post("/workflow/process-command")
async def process_command(request: ProcessCommandRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=25.0) as client:
        access = await _post_json(
            client,
            f"{settings.security_service_url}/access/check",
            {
                "user_id": request.user_id,
                "action": "device:control",
                "resource_type": "device",
                "resource_id": request.device_id or request.device_name or "unknown",
            },
        )
        if not access["allowed"]:
            raise HTTPException(status_code=403, detail=access["reason"])

        intent = None
        action = request.action
        device_name = request.device_name
        if request.source == CommandSource.VOICE or request.command_text:
            intent = await _post_json(
                client,
                f"{settings.voice_service_url}/voice/parse",
                {
                    "text": request.command_text or f"{request.action or ''} {request.device_name or ''}",
                    "user_id": request.user_id,
                    "home_id": request.home_id,
                    "provider": VoiceProvider.DIALOGFLOW.value,
                    "language": "ru",
                },
            )
            if not action:
                action = intent.get("action")
            if not device_name:
                device_name = intent.get("device_name")

        if not action:
            raise HTTPException(status_code=400, detail="Unable to resolve command action")

        device = await _resolve_device(client, request.home_id, request.device_id, device_name)
        command = await _post_json(
            client,
            f"{settings.device_service_url}/devices/{device['device_id']}/command",
            {
                "action": action,
                "params": request.params,
                "source": request.source.value,
                "actor_id": request.user_id,
                "actor_role": request.actor_role.value,
            },
        )

        monitoring = await _post_json(
            client,
            f"{settings.monitoring_service_url}/monitoring/log-command",
            {
                "event_id": str(uuid4()),
                "home_id": request.home_id,
                "user_id": request.user_id,
                "device_id": device["device_id"],
                "action": action,
                "source": request.source.value,
                "success": command["success"],
                "latency_ms": command["latency_ms"],
            },
        )

        await _post_json(
            client,
            f"{settings.monitoring_service_url}/monitoring/energy/ingest",
            {
                "home_id": request.home_id,
                "device_id": device["device_id"],
                "power_w": float(device.get("power_w", 0)),
                "energy_kwh": round(float(device.get("power_w", 0)) / 1000 / 60, 5),
            },
        )

        speech = None
        if request.source == CommandSource.VOICE:
            speech = await _post_json(
                client,
                f"{settings.voice_service_url}/voice/speak",
                {
                    "text": f"Command {action} for {device['name']} completed.",
                    "provider": "dialogflow",
                    "language": "ru",
                },
            )
            await _post_json(
                client,
                f"{settings.notification_service_url}/notify/send",
                {
                    "channel": NotificationChannel.PUSH.value,
                    "recipient": request.user_id,
                    "subject": "Voice command executed",
                    "body": speech["text"],
                    "severity": Severity.INFO.value,
                    "actor_role": request.actor_role.value,
                },
            )

    result = ProcessCommandWorkflowResult(
        intent=intent,
        device=device,
        command=command,
        monitoring=monitoring,
        speech=speech,
    )
    return result.model_dump(mode="json")


@app.post("/workflow/run-scenario")
async def run_scenario(request: RunScenarioRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        access = await _post_json(
            client,
            f"{settings.security_service_url}/access/check",
            {
                "user_id": request.user_id,
                "action": "scenario:manage",
                "resource_type": "scenario",
                "resource_id": request.scenario_id,
            },
        )
        if not access["allowed"]:
            raise HTTPException(status_code=403, detail=access["reason"])

        activation = await _post_json(
            client,
            f"{settings.automation_service_url}/scenarios/{request.scenario_id}/activate",
            {
                "actor_id": request.user_id,
                "actor_role": request.actor_role.value,
                "source": CommandSource.AUTOMATION.value,
            },
        )

        executed = 0
        for item in activation.get("details", []):
            try:
                device = await _resolve_device(client, request.home_id, None, item["device_name"])
                command = await _post_json(
                    client,
                    f"{settings.device_service_url}/devices/{device['device_id']}/command",
                    {
                        "action": item["action"],
                        "params": item.get("params", {}),
                        "source": CommandSource.AUTOMATION.value,
                        "actor_id": request.user_id,
                        "actor_role": request.actor_role.value,
                    },
                )
                await _post_json(
                    client,
                    f"{settings.monitoring_service_url}/monitoring/log-command",
                    {
                        "event_id": str(uuid4()),
                        "home_id": request.home_id,
                        "user_id": request.user_id,
                        "device_id": device["device_id"],
                        "action": item["action"],
                        "source": CommandSource.AUTOMATION.value,
                        "success": command["success"],
                        "latency_ms": command["latency_ms"],
                    },
                )
                executed += 1
            except Exception:
                continue

    return {
        "scenario_id": request.scenario_id,
        "planned_actions": activation.get("planned_actions", 0),
        "executed_actions": executed,
        "success": executed > 0,
    }


@app.get("/dashboard/{home_id}/{user_id}")
async def dashboard(home_id: str, user_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        devices = await _get_json(client, f"{settings.device_service_url}/devices", {"home_id": home_id})
        scenarios = await _get_json(client, f"{settings.automation_service_url}/scenarios", {"home_id": home_id})
        rules = await _get_json(client, f"{settings.automation_service_url}/rules", {"home_id": home_id})
        kpi = await _get_json(client, f"{settings.monitoring_service_url}/monitoring/kpi", {"home_id": home_id})
        logs = await _get_json(
            client,
            f"{settings.monitoring_service_url}/monitoring/commands",
            {"home_id": home_id, "limit": 30},
        )
        anomalies = await _get_json(
            client,
            f"{settings.monitoring_service_url}/monitoring/anomalies",
            {"home_id": home_id},
        )
        users = await _get_json(client, f"{settings.security_service_url}/users", {"home_id": home_id})
        tls = await _get_json(client, f"{settings.security_service_url}/mqtt/tls/status")
        integrations = await _get_json(client, f"{settings.integration_service_url}/integrations/history")
        brands = await _get_json(client, f"{settings.integration_service_url}/brands")
        notifications = await _get_json(client, f"{settings.notification_service_url}/notify/history")
        weather = await _get_json(
            client,
            f"{settings.integration_service_url}/integrations/weather/current",
            {"home_id": home_id},
        )

    return {
        "home_id": home_id,
        "user_id": user_id,
        "devices": devices,
        "scenarios": scenarios,
        "rules": rules,
        "kpi": kpi,
        "command_logs": logs,
        "anomalies": anomalies,
        "users": users,
        "mqtt_tls": tls,
        "integrations": integrations,
        "brands": brands,
        "notifications": notifications,
        "weather": weather,
    }
