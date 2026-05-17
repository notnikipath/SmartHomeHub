# Deployment

## Requirements

- Docker
- Docker Compose
- Python 3.11 for local checks

## Start

```bash
cd d:\Шарага\Кинжибаев\task_9_smarthome
docker compose up --build -d
```

## Stop

```bash
docker compose down
```

## Validate

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Ports

- `8580` API gateway
- `5178` frontend
- `8501-8507` service ports
- `55437` PostgreSQL
- `8087` InfluxDB
- `6384` Redis
- `5673` RabbitMQ
- `1884` MQTT broker