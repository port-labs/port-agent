import json
from pathlib import Path
from typing import Any, Optional, Union

from dotenv import find_dotenv
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    BaseSettings,
    Field,
    parse_file_as,
    parse_obj_as,
    validator,
)


class ActionReport(BaseModel):
    status: str | None = None
    link: str | None = None
    summary: str | None = None
    external_run_id: str | None = Field(None, alias="externalRunId")


class Mapping(BaseModel):
    enabled: bool | str = True
    method: str | None = None
    url: str | None = None
    body: dict[str, Any] | str | None = None
    headers: dict[str, str] | str | None = None
    query: dict[str, str] | str | None = None
    report: ActionReport | None = None
    fieldsToDecryptPaths: list[str] = []


class Settings(BaseSettings):
    USING_LOCAL_PORT_INSTANCE: bool = False
    LOG_LEVEL: str = "INFO"

    STREAMER_NAME: str

    PORT_ORG_ID: str
    PORT_API_BASE_URL: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "https://api.getport.io")
    PORT_CLIENT_ID: str
    PORT_CLIENT_SECRET: str
    KAFKA_CONSUMER_SECURITY_PROTOCOL: str = "plaintext"
    KAFKA_CONSUMER_AUTHENTICATION_MECHANISM: str = "none"
    KAFKA_CONSUMER_SESSION_TIMEOUT_MS: int = 45000
    KAFKA_CONSUMER_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_CONSUMER_GROUP_ID: str = ""

    KAFKA_RUNS_TOPIC: str = ""

    CONTROL_THE_PAYLOAD_CONFIG_PATH: Path = Path("./control_the_payload_config.json")

    AGENT_ENVIRONMENTS: Union[str, list[str]] = Field(default="")

    @validator("AGENT_ENVIRONMENTS", always=True)
    def parse_environments(cls, v: Any) -> list[str]:
        """Parse comma-separated environment list from env var"""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        if isinstance(v, list):
            return v
        return []

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
        env_file = find_dotenv()
        env_file_encoding = "utf-8"

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name == "AGENT_ENVIRONMENTS":
                # Return raw string value, let validator handle parsing
                return raw_val
            # For other fields, use default JSON parsing
            return json.loads(raw_val)

    WEBHOOK_INVOKER_TIMEOUT: float = 30


settings = Settings()

control_the_payload_config = parse_file_as(
    list[Mapping], settings.CONTROL_THE_PAYLOAD_CONFIG_PATH
)
