from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.smarthome_common import (
    IntentType,
    Role,
    Settings,
    VoiceCommandRequest,
    VoiceIntent,
    VoiceProvider,
    VoiceSpeechRequest,
    VoiceSpeechResult,
    parse_voice_command_text,
    voice_accuracy_pct,
)

settings = Settings(service_name="voice-service", service_port=8503)
app = FastAPI(title="SmartHome Voice Service", version="1.0.0")


class AccuracyRequest(BaseModel):
    scores: list[float] = Field(default_factory=list)


AccuracyRequest.model_rebuild()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/voice/parse")
async def parse_command(request: VoiceCommandRequest) -> dict:
    parsed = parse_voice_command_text(request.text)
    intent = VoiceIntent(
        intent_type=parsed.get("intent_type", IntentType.UNKNOWN.value),
        device_name=parsed.get("device_name"),
        action=parsed.get("action"),
        confidence=float(parsed.get("confidence", 0.0)),
    )
    if intent.intent_type == IntentType.UNKNOWN and request.text.strip():
        intent.confidence = 0.4
    return intent.model_dump(mode="json")


@app.post("/voice/speak")
async def speak(request: VoiceSpeechRequest) -> dict:
    return VoiceSpeechResult(text=request.text, provider=request.provider).model_dump(mode="json")


@app.get("/voice/providers")
async def providers() -> dict:
    return {"items": [provider.value for provider in VoiceProvider]}


@app.post("/voice/accuracy")
async def accuracy(request: AccuracyRequest) -> dict:
    return {"accuracy_pct": voice_accuracy_pct(request.scores)}


@app.post("/voice/provider/connect")
async def connect_provider(provider: VoiceProvider, actor_role: Role = Role.OWNER) -> dict:
    if actor_role not in {Role.OWNER, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Only owner or admin can connect providers")
    return {"provider": provider.value, "status": "connected"}