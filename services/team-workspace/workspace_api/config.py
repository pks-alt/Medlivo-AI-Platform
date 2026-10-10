from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKSPACE_", extra="ignore", hide_input_in_errors=True)
    enabled: bool = False
    database_url: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    google_client_id: str = ""
    google_hosted_domain: str = "medlivo.com"
    submission_ai_enabled: bool = False
    submission_ai_project: str = ""
    submission_ai_location: str = "global"
    submission_ai_model: str = ""

    @model_validator(mode="after")
    def check_configuration(self):
        if self.enabled:
            if not self.google_client_id.endswith(".apps.googleusercontent.com"):
                raise ValueError("Configure the approved Google OAuth client ID")
            if not self.google_hosted_domain or "/" in self.google_hosted_domain:
                raise ValueError("Configure an exact Google Workspace hosted domain")
            if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
                raise ValueError("The enabled service requires a private PostgreSQL connection")
            if self.submission_ai_enabled:
                if not self.submission_ai_project or "/" in self.submission_ai_project:
                    raise ValueError("Configure the Vertex AI project for Submission Studio")
                if not self.submission_ai_location or "/" in self.submission_ai_location:
                    raise ValueError("Configure the Vertex AI location for Submission Studio")
                if not self.submission_ai_model or "/" in self.submission_ai_model:
                    raise ValueError("Configure the approved Submission Studio model")
        return self
