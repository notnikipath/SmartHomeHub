# SmartHome Hub

SmartHome Hub is a microservice platform for centralized IoT control. It supports device management, automation scenarios, voice command processing, energy monitoring, security workflows, and third-party integrations.

## Services

- `api-gateway` - orchestration, workflow pipeline, aggregated dashboard
- `device-service` - device registration, command execution, state cache
- `automation-service` - scenarios and if-then rules, import and export
- `voice-service` - NLP parsing, provider connectors, speech response
- `monitoring-service` - command logs, energy analytics, anomaly detection
- `security-service` - role-based access, 2FA flow, MQTT TLS status
- `notification-service` - alerts, incidents, voice notifications
- `integration-service` - brand cloud, smart speakers, weather, HomeKit
- `frontend` - SmartHome dashboard

## Implemented optional improvements

1. User behavior learning with auto-scenario recommendations
2. Energy consumption forecasting
3. Activity anomaly detection
4. Smart speaker integration (Alice, Alexa, Google Home)
5. Redis-based state cache and asynchronous command style
6. Multi-user mode with owner and guest access policies

## Stack

- Backend: Python FastAPI microservices
- Protocols: MQTT, CoAP, HTTP
- Data: PostgreSQL, InfluxDB, Redis
- Queue: RabbitMQ
- Frontend: React + Vite

## Run locally

```bash
cd d:\Шарага\Кинжибаев\task_9_smarthome
docker compose up --build -d
```

## Endpoints

- Frontend: `http://localhost:5178`
- Gateway health: `http://localhost:8580/health`
- Services health: `http://localhost:8580/services/health`
- Swagger: `http://localhost:8580/docs`

## Validation

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo

```bash
python scripts/demo_pipeline.py
```

## Sample data

```bash
python scripts/generate_sample_data.py
```

Output file: `data/samples/smarthome_events.json`