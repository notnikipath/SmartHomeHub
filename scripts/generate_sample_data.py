from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

CATEGORIES = ["lighting", "climate", "security", "appliance", "multimedia"]
PROTOCOLS = ["wifi", "zigbee", "z_wave", "mqtt", "coap", "http"]
ROOMS = ["living_room", "kitchen", "bedroom", "hall", "entry", "garage"]
ACTIONS = ["turn_on", "turn_off", "set_temperature", "set_brightness", "lock", "unlock"]


def make_event(index: int) -> dict:
    home = f"HOME-{(index % 12) + 1:03d}"
    device = f"DEV-{index:05d}"
    return {
        "home_id": home,
        "device_id": device,
        "name": f"device_{index:05d}",
        "category": random.choice(CATEGORIES),
        "protocol": random.choice(PROTOCOLS),
        "room": random.choice(ROOMS),
        "power_w": round(random.uniform(2, 2100), 2),
        "action": random.choice(ACTIONS),
        "latency_ms": round(random.uniform(90, 880), 2),
        "voice_confidence": round(random.uniform(0.82, 0.99), 3),
        "anomaly_score": round(random.uniform(0.1, 3.2), 2),
        "created_at": (datetime.now(UTC) - timedelta(seconds=index * 5)).isoformat(),
    }


if __name__ == "__main__":
    random.seed(17)
    output = Path(__file__).resolve().parents[1] / "data" / "samples" / "smarthome_events.json"
    payload = [make_event(i) for i in range(1, 12001)]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} records to {output}")