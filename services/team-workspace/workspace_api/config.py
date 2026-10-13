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
    outreach_ai_enabled: bool = False
    outreach_ai_project: str = ""
    outreach_ai_location: str = "global"
    outreach_ai_model: str = ""
    gmail_pilot_enabled: bool = False
    gmail_oauth_client_secret: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    gmail_oauth_redirect_uri: str = ""
    gmail_pubsub_topic: str = ""
    gmail_secret_project: str = ""
    submission_packet_download_enabled: bool = False
    submission_document_buckets: str = ""

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
            if self.outreach_ai_enabled:
                if not self.outreach_ai_project or "/" in self.outreach_ai_project:
                    raise ValueError("Configure the Vertex AI project for recruiter outreach")
                if not self.outreach_ai_location or "/" in self.outreach_ai_location:
                    raise ValueError("Configure the Vertex AI location for recruiter outreach")
                if not self.outreach_ai_model or "/" in self.outreach_ai_model:
                    raise ValueError("Configure the approved recruiter outreach model")
            if self.gmail_pilot_enabled:
                if not self.gmail_oauth_client_secret.get_secret_value():
                    raise ValueError("Configure the Gmail OAuth client secret")
                if not self.gmail_oauth_redirect_uri.startswith("https://"):
                    raise ValueError("Configure the HTTPS Gmail OAuth redirect URI")
                if not self.gmail_pubsub_topic.startswith("projects/") or "/topics/" not in self.gmail_pubsub_topic:
                    raise ValueError("Configure the Gmail Pub/Sub topic")
                if not self.gmail_secret_project or "/" in self.gmail_secret_project:
                    raise ValueError("Configure the Google Secret Manager project for Gmail")
            if self.submission_packet_download_enabled:
                buckets = [x.strip() for x in self.submission_document_buckets.split(",") if x.strip()]
                if not buckets or any("/" in x or ":" in x for x in buckets):
                    raise ValueError("Configure approved GCS buckets for Submission Studio documents")
        return self
