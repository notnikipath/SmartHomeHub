from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DeviceCategory(str, Enum):
    LIGHTING = "lighting"
    CLIMATE = "climate"
    SECURITY = "security"
    APPLIANCE = "appliance"
    MULTIMEDIA = "multimedia"


class DeviceProtocol(str, Enum):
    WIFI = "wifi"
    ZIGBEE = "zigbee"
    Z_WAVE = "z_wave"
    MQTT = "mqtt"
    COAP = "coap"
    HTTP = "http"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class TriggerType(str, Enum):
    TIME = "time"
    SENSOR = "sensor"
    MANUAL = "manual"
    GEO = "geo"


class IntentType(str, Enum):
    DEVICE_CONTROL = "device_control"
    SCENARIO_ACTIVATE = "scenario_activate"
    STATUS_QUERY = "status_query"
    UNKNOWN = "unknown"


class VoiceProvider(str, Enum):
    ALISA = "alisa"
    GOOGLE_HOME = "google_home"
    ALEXA = "alexa"
    DIALOGFLOW = "dialogflow"


class CommandSource(str, Enum):
    UI = "ui"
    VOICE = "voice"
    AUTOMATION = "automation"


class NotificationChannel(str, Enum):
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    VOICE = "voice"
    WEBHOOK = "webhook"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Role(str, Enum):
    OWNER = "owner"
    GUEST = "guest"
    ADMIN = "admin"


class Device(BaseModel):
    device_id: str
    home_id: str
    name: str
    room: str
    category: DeviceCategory
    protocol: DeviceProtocol
    brand: str
    model: str
    status: DeviceStatus = DeviceStatus.ONLINE
    online: bool = True
    power_w: float = Field(ge=0, default=0)
    state: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)
    last_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeviceRegisterRequest(BaseModel):
    home_id: str
    name: str
    room: str
    category: DeviceCategory
    protocol: DeviceProtocol
    brand: str
    model: str
    capabilities: list[str] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class DeviceCommandRequest(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    source: CommandSource = CommandSource.UI
    actor_id: str
    actor_role: Role


class DeviceCommandResult(BaseModel):
    command_id: str
    device_id: str
    action: str
    success: bool
    latency_ms: float = Field(ge=0)
    queued: bool = False
    previous_state: dict[str, Any] = Field(default_factory=dict)
    new_state: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RuleCondition(BaseModel):
    sensor: str
    operator: str
    value: str


class RuleAction(BaseModel):
    device_name: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class AutomationRuleCreateRequest(BaseModel):
    home_id: str
    name: str
    trigger: TriggerType
    condition: RuleCondition
    actions: list[RuleAction] = Field(default_factory=list)
    enabled: bool = True
    actor_id: str
    actor_role: Role


class AutomationRule(BaseModel):
    rule_id: str
    home_id: str
    name: str
    trigger: TriggerType
    condition: RuleCondition
    actions: list[RuleAction] = Field(default_factory=list)
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScenarioCreateRequest(BaseModel):
    home_id: str
    name: str
    description: str = ""
    actions: list[RuleAction] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class Scenario(BaseModel):
    scenario_id: str
    home_id: str
    name: str
    description: str
    actions: list[RuleAction] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScenarioActivationRequest(BaseModel):
    actor_id: str
    actor_role: Role
    source: CommandSource = CommandSource.AUTOMATION


class ScenarioExecutionResult(BaseModel):
    scenario_id: str
    success: bool
    planned_actions: int
    executed_actions: int
    details: list[dict[str, Any]] = Field(default_factory=list)
    activated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VoiceCommandRequest(BaseModel):
    text: str
    user_id: str
    home_id: str
    provider: VoiceProvider = VoiceProvider.DIALOGFLOW
    language: str = Field(default="ru", pattern="^(ru|en)$")


class VoiceIntent(BaseModel):
    intent_type: IntentType = IntentType.UNKNOWN
    device_name: str | None = None
    action: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1, default=0)


class VoiceSpeechRequest(BaseModel):
    text: str
    provider: VoiceProvider = VoiceProvider.DIALOGFLOW
    language: str = Field(default="ru", pattern="^(ru|en)$")


class VoiceSpeechResult(BaseModel):
    text: str
    provider: VoiceProvider
    spoken_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CommandLogEvent(BaseModel):
    event_id: str
    home_id: str
    user_id: str
    device_id: str
    action: str
    source: CommandSource
    success: bool
    latency_ms: float = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EnergySample(BaseModel):
    sample_id: str
    home_id: str
    device_id: str
    timestamp: datetime
    power_w: float = Field(ge=0)
    energy_kwh: float = Field(ge=0)


class AnomalyEvent(BaseModel):
    anomaly_id: str
    home_id: str
    metric: str
    value: float
    threshold: float
    severity: Severity
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserAccount(BaseModel):
    user_id: str
    home_id: str
    role: Role
    email: str
    phone: str
    enabled: bool = True
    two_factor_enabled: bool = True


class TwoFactorStartRequest(BaseModel):
    user_id: str
    password: str


class TwoFactorChallenge(BaseModel):
    challenge_id: str
    user_id: str
    otp_code: str
    channel: NotificationChannel = NotificationChannel.SMS
    expires_at: datetime


class TwoFactorVerifyRequest(BaseModel):
    challenge_id: str
    otp_code: str


class AccessCheckRequest(BaseModel):
    user_id: str
    action: str
    resource_type: str = "device"
    resource_id: str = "*"


class AccessCheckResult(BaseModel):
    allowed: bool
    reason: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationSyncRequest(BaseModel):
    system_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    actor_id: str
    actor_role: Role


class IntegrationSyncResult(BaseModel):
    sync_id: str
    system_name: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationRequest(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    actor_role: Role


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProcessCommandWorkflowResult(BaseModel):
    intent: dict[str, Any] | None
    device: dict[str, Any]
    command: dict[str, Any]
    monitoring: dict[str, Any]
    speech: dict[str, Any] | None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))