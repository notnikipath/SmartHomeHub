from __future__ import annotations

from statistics import mean, pstdev

from .schemas import DeviceProtocol


def forecast_energy_kwh(samples: list[float], horizon_hours: int = 24) -> float:
    if not samples:
        return 0.0
    recent = samples[-24:] if len(samples) > 24 else samples
    avg = mean(recent)
    trend = (recent[-1] - recent[0]) / max(len(recent), 1)
    projected = max(0.0, avg + trend * min(horizon_hours, 24) * 0.2)
    return round(projected, 3)


def detect_anomaly_score(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    mu = mean(values)
    sigma = pstdev(values)
    if sigma == 0:
        return 0.0
    z_score = abs(values[-1] - mu) / sigma
    return round(z_score, 2)


def is_anomalous(values: list[float], threshold: float = 2.5) -> bool:
    return detect_anomaly_score(values) >= threshold


def command_latency_estimate_ms(protocol: DeviceProtocol, queue_depth: int, edge_enabled: bool = False) -> float:
    base = {
        DeviceProtocol.MQTT: 280,
        DeviceProtocol.COAP: 330,
        DeviceProtocol.ZIGBEE: 370,
        DeviceProtocol.Z_WAVE: 420,
        DeviceProtocol.WIFI: 260,
        DeviceProtocol.HTTP: 300,
    }[protocol]
    queue_penalty = queue_depth * 8.5
    edge_bonus = 95 if edge_enabled else 0
    return round(max(85.0, base + queue_penalty - edge_bonus), 2)


def availability_pct(uptime_minutes: int, total_minutes: int) -> float:
    if total_minutes <= 0:
        return 0.0
    return round(min(max((uptime_minutes / total_minutes) * 100, 0.0), 100.0), 3)


def voice_accuracy_pct(scores: list[float]) -> float:
    if not scores:
        return 0.0
    bounded = [min(max(score, 0.0), 1.0) for score in scores]
    return round(mean(bounded) * 100, 2)