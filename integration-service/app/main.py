from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.smarthome_common import IntegrationSyncRequest, IntegrationSyncResult, Role, Settings, has_permission

settings = Settings(service_name="integration-service", service_port=8507)
app = FastAPI(title="SmartHome Integration Service", version="1.0.0")

history: list[IntegrationSyncResult] = [
    IntegrationSyncResult(
        sync_id="SYNC-SEED-1",
        system_name="brand_cloud",
        status="ok",
        details={"brand": "Xiaomi", "devices_connected": 5},
    )
]

brands = ["Xiaomi", "Philips", "Samsung"]


def _assert_manage(role: Role) -> None:
    if not has_permission(role, "integration:manage"):
        raise HTTPException(status_code=403, detail="Forbidden")


def _push(system_name: str, details: dict[str, Any]) -> dict[str, Any]:
    event = IntegrationSyncResult(sync_id=str(uuid4()), system_name=system_name, status="ok", details=details)
    history.append(event)
    return event.model_dump(mode="json")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/brands")
async def list_brands() -> dict[str, Any]:
    return {"items": brands, "count": len(brands)}


@app.post("/integrations/brand/connect")
async def connect_brand(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_manage(request.actor_role)
    brand = request.payload.get("brand", "Unknown")
    if brand not in brands:
        raise HTTPException(status_code=400, detail="Unsupported brand")
    return _push("brand_connect", {"brand": brand, "linked_devices": request.payload.get("linked_devices", 0)})


@app.post("/integrations/smart-speaker/connect")
async def connect_speaker(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_manage(request.actor_role)
    provider = request.payload.get("provider", "alisa")
    if provider not in {"alisa", "alexa", "google_home"}:
        raise HTTPException(status_code=400, detail="Unsupported speaker provider")
    return _push("smart_speaker", {"provider": provider, "status": "connected"})


@app.get("/integrations/weather/current")
async def weather(home_id: str = "HOME-DEMO") -> dict[str, Any]:
    details = {
        "home_id": home_id,
        "provider": "open-meteo",
        "temperature_c": 18.4,
        "humidity_pct": 62,
        "condition": "cloudy",
        "updated_at": datetime.now(UTC),
    }
    return details


@app.post("/integrations/homekit/pair")
async def pair_homekit(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_manage(request.actor_role)
    return _push("homekit", {"paired": True, "home_id": request.payload.get("home_id", "HOME-DEMO")})


@app.post("/integrations/sync")
async def generic_sync(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_manage(request.actor_role)
    return _push(request.system_name, request.payload)


@app.get("/integrations/history")
async def get_history(system_name: str | None = None) -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in history if not system_name or item.system_name == system_name]
    return {"items": items, "count": len(items)}