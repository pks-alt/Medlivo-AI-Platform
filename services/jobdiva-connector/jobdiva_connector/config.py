from pydantic_settings import BaseSettings, SettingsConfigDict


class JobDivaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JOBDIVA_",
        env_file=".env",
        extra="ignore",
    )

    client_id: str
    username: str
    password: str
    api_base_url: str
    request_timeout_seconds: float = 30.0


settings = JobDivaSettings()
