from typing import Optional

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"

    STREAMER_NAME: str

    PORT_ORG_ID: str
    PORT_CLIENT_ID: str = ""
    PORT_CLIENT_SECRET: str = ""
    PORT_API_URL: str = "https://api.getport.io/v1"
    GITLAB_URL: str = "https://gitlab.com/"
    KAFKA_CONSUMER_BROKERS: str = "localhost:9092"
    KAFKA_CONSUMER_SECURITY_PROTOCOL: str = "plaintext"
    KAFKA_CONSUMER_AUTHENTICATION_MECHANISM: str = "none"
    KAFKA_CONSUMER_USERNAME: str = "local"
    KAFKA_CONSUMER_PASSWORD: str = ""
    KAFKA_CONSUMER_SESSION_TIMEOUT_MS: int = 45000
    KAFKA_CONSUMER_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_CONSUMER_GROUP_ID: str = ""

    KAFKA_RUNS_TOPIC: str = ""

    @validator("KAFKA_RUNS_TOPIC", always=True)
    def set_kafka_runs_topic(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return f"{values.get('PORT_ORG_ID')}.runs"

    KAFKA_CHANGE_LOG_TOPIC: str = ""

    @validator("KAFKA_CHANGE_LOG_TOPIC", always=True)
    def set_kafka_change_log_topic(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return f"{values.get('PORT_ORG_ID')}.change.log"

    class Config:
        case_sensitive = True

    WEBHOOK_ASYNC_INVOKER_TIMEOUT: int = 5
    WEBHOOK_SYNC_INVOKER_TIMEOUT: int = 30
    GITLAB_PIPELINE_INVOKER_TIMEOUT: int = 5


settings = Settings()
