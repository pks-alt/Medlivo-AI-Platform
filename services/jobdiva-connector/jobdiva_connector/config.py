from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class JobDivaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JOBDIVA_",
        env_file=".env",
        extra="ignore",
    )

    client_id: int
    username: str
    password: str
    api_base_url: str = "https://api.jobdiva.com"
    authorization_prefix: str = ""
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=120)

    @field_validator("api_base_url")
    @classmethod
    def require_jobdiva_https(cls, value: str) -> str:
        value = value.rstrip("/")
        if value != "https://api.jobdiva.com":
            raise ValueError("JobDiva API base URL must be https://api.jobdiva.com")
        return value

    @field_validator("authorization_prefix")
    @classmethod
    def validate_authorization_prefix(cls, value: str) -> str:
        if value not in {"", "Bearer"}:
            raise ValueError("Authorization prefix must be empty or Bearer")
        return value

