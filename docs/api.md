# API Overview

## Gateway

- `POST /auth/challenge/start`
- `POST /auth/challenge/verify`
- `POST /workflow/process-command`
- `POST /workflow/run-scenario`
- `GET /dashboard/{home_id}/{user_id}`
- `GET /services/health`

## Device service

- `GET /devices`
- `GET /devices/{device_id}`
- `GET /devices/search`
- `POST /devices`
- `POST /devices/{device_id}/command`
- `GET /states/cache`

## Automation service

- `GET /scenarios`
- `POST /scenarios`
- `POST /scenarios/{scenario_id}/activate`
- `GET /rules`
- `POST /rules`
- `GET /rules/export`
- `POST /rules/import`

## Voice service

- `POST /voice/parse`
- `POST /voice/speak`
- `GET /voice/providers`
- `POST /voice/accuracy`

## Monitoring service

- `POST /monitoring/log-command`
- `POST /monitoring/energy/ingest`
- `GET /monitoring/commands`
- `GET /monitoring/kpi`
- `POST /monitoring/anomaly/check`
- `GET /monitoring/anomalies`

## Security service

- `POST /auth/challenge/start`
- `POST /auth/challenge/verify`
- `POST /access/check`
- `GET /users`
- `GET /mqtt/tls/status`
- `GET /audit`

## Notification service

- `POST /notify/send`
- `POST /notify/incident`
- `POST /notify/voice`
- `GET /notify/history`

## Integration service

- `GET /brands`
- `POST /integrations/brand/connect`
- `POST /integrations/smart-speaker/connect`
- `GET /integrations/weather/current`
- `POST /integrations/homekit/pair`
- `GET /integrations/history`
