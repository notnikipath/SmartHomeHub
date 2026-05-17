from shared.smarthome_common import (
    DeviceProtocol,
    availability_pct,
    command_latency_estimate_ms,
    detect_anomaly_score,
    forecast_energy_kwh,
    is_anomalous,
    voice_accuracy_pct,
)


def test_forecast_energy() -> None:
    value = forecast_energy_kwh([0.3, 0.4, 0.5, 0.6], horizon_hours=24)
    assert value >= 0


def test_anomaly_helpers() -> None:
    score = detect_anomaly_score([10, 11, 12, 45])
    assert score >= 0
    assert is_anomalous([10, 11, 12, 45], threshold=1.5)


def test_latency_and_availability() -> None:
    latency = command_latency_estimate_ms(DeviceProtocol.MQTT, queue_depth=3, edge_enabled=True)
    assert latency > 0
    assert availability_pct(43180, 43200) > 99


def test_voice_accuracy() -> None:
    assert voice_accuracy_pct([0.95, 0.97, 0.96]) >= 95
