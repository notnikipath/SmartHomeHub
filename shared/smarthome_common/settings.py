from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "smarthome-service"
    service_port: int = 8500
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://smarthome:smarthome@postgres:5432/smarthome"
    influx_url: str = "http://influxdb:8086"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    mqtt_broker_url: str = "mqtt://mosquitto:1883"

    jwt_secret: str = "smarthome-dev-secret"
    encryption_key: str = "smarthome-dev-encryption-key"

    command_latency_target_ms: float = 1000.0
    availability_target_pct: float = 99.9
    device_capacity_target: int = 10000
    voice_accuracy_target_pct: float = 95.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()