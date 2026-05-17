from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.smarthome_common import (
    CommandSource,
    Device,
    DeviceCategory,
    DeviceCommandRequest,
    DeviceCommandResult,
    DeviceProtocol,
    DeviceRegisterRequest,
    DeviceStatus,
    Role,
    Settings,
    TTLCache,
    build_audit_event,
    command_latency_estimate_ms,
    has_permission,
)

settings = Settings(service_name="device-service", service_port=8501)
app = FastAPI(title="SmartHome Device Service", version="1.0.0")

state_cache = TTLCache(ttl_seconds=180)
audit_log: list[dict] = []


def _seed_devices() -> dict[str, Device]:
    now = datetime.now(UTC)
    devices = {
        "DEV-LIGHT-1": Device(
            device_id="DEV-LIGHT-1",
            home_id="HOME-DEMO",
            name="living room light",
            room="living_room",
            category=DeviceCategory.LIGHTING,
            protocol=DeviceProtocol.ZIGBEE,
            brand="Philips",
            model="Hue A19",
            power_w=12,
            state={"on": True, "brightness": 65},
            capabilities=["turn_on", "turn_off", "set_brightness"],
            last_seen=now,
        ),
        "DEV-THERM-1": Device(
            device_id="DEV-THERM-1",
            home_id="HOME-DEMO",
            name="hall thermostat",
            room="hall",
            category=DeviceCategory.CLIMATE,
            protocol=DeviceProtocol.WIFI,
            brand="Xiaomi",
            model="Mi Thermostat",
            power_w=38,
            state={"on": True, "temperature": 22},
            capabilities=["turn_on", "turn_off", "set_temperature"],
            last_seen=now,
        ),
        "DEV-DOOR-1": Device(
            device_id="DEV-DOOR-1",
            home_id="HOME-DEMO",
            name="front door lock",
            room="entry",
            category=DeviceCategory.SECURITY,
            protocol=DeviceProtocol.Z_WAVE,
            brand="Samsung",
            model="Smart Lock",
            power_w=4,
            state={"locked": True},
            capabilities=["lock", "unlock", "status"],
            last_seen=now,
        ),
        "DEV-SPEAKER-1": Device(
            device_id="DEV-SPEAKER-1",
            home_id="HOME-DEMO",
            name="kitchen speaker",
            room="kitchen",
            category=DeviceCategory.MULTIMEDIA,
            protocol=DeviceProtocol.WIFI,
            brand="Yandex",
            model="Station Mini",
            power_w=9,
            state={"on": True, "volume": 35},
            capabilities=["turn_on", "turn_off", "set_volume"],
            last_seen=now,
        ),
    }
    for device in devices.values():
        state_cache.set(device.device_id, device.state)
    return devices


devices = _seed_devices()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="device",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _apply_action(device: Device, action: str, params: dict) -> None:
    if action == "turn_on":
        device.state["on"] = True
        device.online = True
        device.status = DeviceStatus.ONLINE
    elif action == "turn_off":
        device.state["on"] = False
    elif action == "set_brightness":
        device.state["brightness"] = max(0, min(100, int(params.get("brightness", 50))))
        device.state["on"] = device.state.get("brightness", 0) > 0
    elif action == "set_temperature":
        device.state["temperature"] = max(16, min(30, int(params.get("temperature", 22))))
    elif action == "set_volume":
        device.state["volume"] = max(0, min(100, int(params.get("volume", 30))))
    elif action == "lock":
        device.state["locked"] = True
    elif action == "unlock":
        device.state["locked"] = False
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/devices")
async def list_devices(home_id: str = "HOME-DEMO", category: DeviceCategory | None = None) -> dict:
    items = []
    for device in devices.values():
        if device.home_id != home_id:
            continue
        if category and device.category != category:
            continue
        items.append(device.model_dump(mode="json"))
    return {"items": items, "count": len(items)}


@app.get("/devices/search")
async def find_device(name: str, home_id: str = "HOME-DEMO") -> dict:
    name_norm = name.lower().strip()
    for device in devices.values():
        if device.home_id == home_id and name_norm in device.name.lower():
            return device.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Device not found")


@app.get("/devices/{device_id}")
async def get_device(device_id: str, actor_role: Role = Role.OWNER) -> dict:
    _assert_permission(actor_role, "device:read")
    device = devices.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device.model_dump(mode="json")


@app.post("/devices")
async def register_device(request: DeviceRegisterRequest) -> dict:
    _assert_permission(request.actor_role, "device:register")
    device = Device(
        device_id=str(uuid4()),
        home_id=request.home_id,
        name=request.name,
        room=request.room,
        category=request.category,
        protocol=request.protocol,
        brand=request.brand,
        model=request.model,
        capabilities=request.capabilities,
        state={"on": False},
    )
    devices[device.device_id] = device
    state_cache.set(device.device_id, device.state)
    _audit(request.actor_id, request.actor_role, "device.register", device.device_id)
    return device.model_dump(mode="json")


@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, request: DeviceCommandRequest) -> dict:
    _assert_permission(request.actor_role, "device:control")
    device = devices.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    if request.actor_role == Role.GUEST and device.category == DeviceCategory.SECURITY:
        raise HTTPException(status_code=403, detail="Guest cannot control security devices")

    previous_state = dict(device.state)
    _apply_action(device, request.action, request.params)
    device.last_seen = datetime.now(UTC)

    queue_depth = 2 if request.source == CommandSource.AUTOMATION else 1
    latency_ms = command_latency_estimate_ms(device.protocol, queue_depth=queue_depth, edge_enabled=True)
    result = DeviceCommandResult(
        command_id=str(uuid4()),
        device_id=device.device_id,
        action=request.action,
        success=True,
        latency_ms=latency_ms,
        queued=request.source == CommandSource.AUTOMATION,
        previous_state=previous_state,
        new_state=dict(device.state),
    )

    state_cache.set(device.device_id, dict(device.state))
    _audit(request.actor_id, request.actor_role, "device.command", device.device_id, {"action": request.action})
    return result.model_dump(mode="json")


@app.get("/states/cache")
async def cached_states() -> dict:
    items = []
    for device in devices.values():
        cached = state_cache.get(device.device_id)
        items.append({"device_id": device.device_id, "state": cached or device.state})
    return {"items": items, "count": len(items)}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
