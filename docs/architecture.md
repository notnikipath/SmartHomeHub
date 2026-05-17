# Architecture

## Overview

SmartHome Hub is split into domain microservices with a gateway orchestration layer. The platform covers the end-to-end command lifecycle from UI or voice input to command execution, monitoring, and notifications.

## Core modules

- `device-service`: Wi-Fi, Zigbee, Z-Wave device registry and command dispatch
- `automation-service`: rule engine and scenario management
- `voice-service`: intent parsing and speech responses
- `monitoring-service`: energy analytics, event history, anomaly alerts
- `security-service`: role-based access, 2FA, access logs, TLS status
- `notification-service`: critical and informational notifications
- `integration-service`: brand and ecosystem connectors

## Data layer

- PostgreSQL for metadata and account context
- InfluxDB for telemetry and time-series metrics
- Redis for fast device state cache
- RabbitMQ for asynchronous command and notification flow

## Command pipeline

1. User sends command from UI or voice
2. Gateway validates permissions through `security-service`
3. Voice text is parsed in `voice-service` when needed
4. Device command is executed in `device-service`
5. Event and latency are stored in `monitoring-service`
6. Speech response and notification are sent if required

## Scalability strategy

- Stateless FastAPI services for horizontal scaling
- Redis cache to reduce device state lookup latency
- Queue-based async handling for notification bursts
- Dedicated monitoring service for heavy analytics workload