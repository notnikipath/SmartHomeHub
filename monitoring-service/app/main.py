from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from statistics import mean
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from shared.smarthome_common import (
    AnomalyEvent,
    CommandLogEvent,
    EnergySample,
    Settings,
    Severity,
    availability_pct,
    detect_anomaly_score,
    forecast_energy_kwh,
    is_anomalous,
)

settings = Settings(service_name="monitoring-service", service_port=8504)
app = FastAPI(title="SmartHome Monitoring Service", version="1.0.0")

command_logs: list[CommandLogEvent] = []
energy_samples: list[EnergySample] = []
anomaly_events: list[AnomalyEvent] = []
voice_scores: list[float] = [0.96, 0.95, 0.97]
availability_minutes: dict[str, tuple[int, int]] = {"HOME-DEMO": (43180, 43200)}


class EnergyIngestRequest(BaseModel):
    home_id: str
    device_id: str
    power_w: float = Field(ge=0)
    energy_kwh: float = Field(ge=0)


class AnomalyCheckRequest(BaseModel):
    home_id: str
    metric: str
    values: list[float] = Field(default_factory=list)
    threshold: float = 2.5


class VoiceAccuracyIngestRequest(BaseModel):
    score: float = Field(ge=0, le=1)


EnergyIngestRequest.model_rebuild()
AnomalyCheckRequest.model_rebuild()
VoiceAccuracyIngestRequest.model_rebuild()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/monitoring/log-command")
async def log_command(event: CommandLogEvent) -> dict[str, Any]:
    command_logs.append(event)
    return {"status": "accepted", "event_id": event.event_id}


@app.get("/monitoring/commands")
async def command_history(home_id: str = "HOME-DEMO", limit: int = 100) -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in command_logs if item.home_id == home_id][-limit:]
    return {"items": items, "count": len(items)}


@app.post("/monitoring/energy/ingest")
async def ingest_energy(request: EnergyIngestRequest) -> dict[str, Any]:
    sample = EnergySample(
        sample_id=str(uuid4()),
        home_id=request.home_id,
        device_id=request.device_id,
        timestamp=datetime.now(UTC),
        power_w=request.power_w,
        energy_kwh=request.energy_kwh,
    )
    energy_samples.append(sample)
    return {"status": "accepted", "sample_id": sample.sample_id}


@app.get("/monitoring/energy/{home_id}")
async def energy_history(home_id: str) -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in energy_samples if item.home_id == home_id]
    return {"items": items, "count": len(items)}


@app.post("/monitoring/anomaly/check")
async def anomaly_check(request: AnomalyCheckRequest) -> dict[str, Any]:
    score = detect_anomaly_score(request.values)
    anomalous = is_anomalous(request.values, threshold=request.threshold)
    event = None
    if anomalous:
        event = AnomalyEvent(
            anomaly_id=str(uuid4()),
            home_id=request.home_id,
            metric=request.metric,
            value=request.values[-1],
            threshold=request.threshold,
            severity=Severity.CRITICAL,
            message=f"Anomaly detected for {request.metric}",
        )
        anomaly_events.append(event)
    return {"anomalous": anomalous, "score": score, "event": event.model_dump(mode="json") if event else None}


@app.post("/monitoring/voice/accuracy")
async def ingest_voice_accuracy(request: VoiceAccuracyIngestRequest) -> dict[str, Any]:
    voice_scores.append(request.score)
    return {"status": "accepted", "samples": len(voice_scores)}


@app.get("/monitoring/kpi")
async def kpi(home_id: str = "HOME-DEMO") -> dict[str, Any]:
    home_commands = [item for item in command_logs if item.home_id == home_id]
    avg_latency = round(mean([item.latency_ms for item in home_commands]), 2) if home_commands else 320.0
    energy_by_device: dict[str, float] = defaultdict(float)
    for sample in energy_samples:
        if sample.home_id == home_id:
            energy_by_device[sample.device_id] += sample.energy_kwh
    forecast = forecast_energy_kwh(list(energy_by_device.values()) or [0.5, 0.4, 0.6], horizon_hours=24)

    uptime, total = availability_minutes.get(home_id, (43100, 43200))
    return {
        "command_reaction_ms": avg_latency,
        "availability_pct": availability_pct(uptime, total),
        "voice_accuracy_pct": round(mean(voice_scores) * 100, 2) if voice_scores else 0.0,
        "energy_forecast_kwh": forecast,
        "anomalies_count": len([item for item in anomaly_events if item.home_id == home_id]),
        "target_command_reaction_ms": settings.command_latency_target_ms,
        "target_availability_pct": settings.availability_target_pct,
        "target_voice_accuracy_pct": settings.voice_accuracy_target_pct,
        "capacity_target_devices": settings.device_capacity_target,
    }


@app.get("/monitoring/anomalies")
async def list_anomalies(home_id: str = "HOME-DEMO") -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in anomaly_events if item.home_id == home_id]
    return {"items": items, "count": len(items)}
