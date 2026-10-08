from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlsplit


class JobDivaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JOBDIVA_",
        extra="ignore",
        hide_input_in_errors=True,
    )

    live_enabled: bool = False
    client_id: str = ""
    username: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    password: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    api_base_url: str = "https://api.jobdiva.com"
    authorization_prefix: str = ""
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=60)
    max_response_bytes: int = Field(default=10_000_000, gt=0, le=50_000_000)
    requests_per_minute: int = Field(default=6, ge=1, le=60)
    requests_per_day: int = Field(default=1000, ge=1, le=100_000)
    max_retry_after_seconds: int = Field(default=60, ge=1, le=300)

    @model_validator(mode="after")
    def validate_settings(self):
        if self.authorization_prefix not in {"", "Bearer"}:
            raise ValueError("Authorization prefix must be empty or Bearer")
        url = urlsplit(self.api_base_url)
        if (
            url.scheme != "https"
            or url.hostname not in {"api.jobdiva.com", "next.jobdiva.com"}
            or url.username
            or url.password
            or url.port
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError("Use an approved HTTPS JobDiva API origin")
        self.api_base_url = self.api_base_url.rstrip("/")
        if not self.live_enabled:
            return self
        if not (self.client_id.isascii() and self.client_id.isdigit() and int(self.client_id) > 0):
            raise ValueError("A positive JobDiva client ID is required")
        if not self.username.get_secret_value() or not self.password.get_secret_value():
            raise ValueError("JobDiva API credentials are required")
        return self
