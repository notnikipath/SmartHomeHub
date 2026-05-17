from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.smarthome_common import (
    AccessCheckRequest,
    AccessCheckResult,
    NotificationChannel,
    Role,
    Settings,
    TwoFactorChallenge,
    TwoFactorStartRequest,
    TwoFactorVerifyRequest,
    UserAccount,
    build_audit_event,
    has_permission,
    sign_token,
)

settings = Settings(service_name="security-service", service_port=8505)
app = FastAPI(title="SmartHome Security Service", version="1.0.0")

users: dict[str, UserAccount] = {
    "USR-OWNER-1": UserAccount(
        user_id="USR-OWNER-1",
        home_id="HOME-DEMO",
        role=Role.OWNER,
        email="owner@demo.local",
        phone="+10000000001",
    ),
    "USR-GUEST-1": UserAccount(
        user_id="USR-GUEST-1",
        home_id="HOME-DEMO",
        role=Role.GUEST,
        email="guest@demo.local",
        phone="+10000000002",
    ),
    "USR-ADMIN-1": UserAccount(
        user_id="USR-ADMIN-1",
        home_id="HOME-DEMO",
        role=Role.ADMIN,
        email="admin@demo.local",
        phone="+10000000003",
    ),
}
passwords = {"USR-OWNER-1": "owner123", "USR-GUEST-1": "guest123", "USR-ADMIN-1": "admin123"}
challenges: dict[str, TwoFactorChallenge] = {}
audit_log: list[dict[str, Any]] = []


def _audit(
    actor_id: str,
    actor_role: Role | str,
    action: str,
    object_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="security",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/challenge/start")
async def start_challenge(request: TwoFactorStartRequest) -> dict[str, Any]:
    user = users.get(request.user_id)
    if user is None or not user.enabled:
        raise HTTPException(status_code=404, detail="User not found or disabled")
    if passwords.get(request.user_id) != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    challenge = TwoFactorChallenge(
        challenge_id=str(uuid4()),
        user_id=request.user_id,
        otp_code="123456",
        channel=NotificationChannel.SMS,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    challenges[challenge.challenge_id] = challenge
    _audit(request.user_id, user.role, "auth.challenge.start", challenge.challenge_id)
    return {
        "challenge_id": challenge.challenge_id,
        "channel": challenge.channel.value,
        "delivery_hint": "***0001",
        "otp_preview": challenge.otp_code,
        "expires_at": challenge.expires_at,
    }


@app.post("/auth/challenge/verify")
async def verify_challenge(request: TwoFactorVerifyRequest) -> dict[str, Any]:
    challenge = challenges.get(request.challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Challenge expired")
    if challenge.otp_code != request.otp_code:
        raise HTTPException(status_code=401, detail="Invalid OTP")

    user = users[challenge.user_id]
    token = sign_token(
        {"sub": user.user_id, "home_id": user.home_id, "role": user.role.value},
        settings.jwt_secret,
        exp_minutes=240,
    )
    _audit(user.user_id, user.role, "auth.challenge.verify", challenge.challenge_id)
    return {"access_token": token, "token_type": "Bearer", "role": user.role.value, "home_id": user.home_id}


@app.post("/access/check")
async def access_check(request: AccessCheckRequest) -> dict[str, Any]:
    user = users.get(request.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    allowed = has_permission(user.role, request.action)
    reason = "permission_granted" if allowed else "permission_denied"
    if allowed and user.role == Role.GUEST and request.resource_type == "security_device":
        allowed = False
        reason = "guest_cannot_control_security_device"

    _audit(user.user_id, user.role, "access.check", request.resource_id, {"action": request.action, "allowed": allowed})
    return AccessCheckResult(allowed=allowed, reason=reason).model_dump(mode="json")


@app.get("/users")
async def list_users(home_id: str = "HOME-DEMO") -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in users.values() if item.home_id == home_id]
    return {"items": items, "count": len(items)}


@app.get("/mqtt/tls/status")
async def mqtt_tls_status() -> dict[str, Any]:
    return {
        "enabled": True,
        "broker": settings.mqtt_broker_url,
        "protocol": "TLSv1.3",
        "certificate_rotation_days": 30,
    }


@app.get("/audit")
async def get_audit(limit: int = 200, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    if not has_permission(actor_role, "audit:read"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"items": audit_log[-limit:], "count": len(audit_log)}
