from __future__ import annotations
import base64
import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone


GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SCOPES = (GMAIL_SEND_SCOPE, GMAIL_READONLY_SCOPE)


@dataclass(frozen=True)
class GmailTokenExchange:
    access_token: str
    refresh_token: str
    scope: list[str]
    expires_in: int


@dataclass(frozen=True)
class GmailProfile:
    email_address: str
    history_id: str | None


@dataclass(frozen=True)
class GmailWatch:
    history_id: str
    expiration: datetime


@dataclass(frozen=True)
class GmailSendReceipt:
    message_id: str
    thread_id: str | None


class GmailProviderError(Exception):
    pass


class GmailSecretStore:
    """Refresh-token persistence through Google Secret Manager.

    The application database stores only the returned resource name.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id

    def put_refresh_token(self, recruiter_user_id: str, refresh_token: str) -> str:
        if not refresh_token:
            raise GmailProviderError("Gmail did not return a refresh token")
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{self.project_id}"
        secret_id = "gmail-recruiter-" + recruiter_user_id.replace("-", "")
        secret_name = f"{parent}/secrets/{secret_id}"
        try:
            client.get_secret(request={"name": secret_name})
        except Exception:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        version = client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": refresh_token.encode("utf-8")},
            }
        )
        return version.name

    def get_refresh_token(self, secret_resource: str) -> str:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": secret_resource})
        value = response.payload.data.decode("utf-8").strip()
        if not value:
            raise GmailProviderError("Stored Gmail refresh token is empty")
        return value

    def destroy_refresh_token(self, secret_resource: str) -> None:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        try:
            client.destroy_secret_version(request={"name": secret_resource})
        except Exception:
            # Disconnect must remain safe/idempotent even if a version was already removed.
            return


class GmailProvider:
    def __init__(self, *, client_id: str, client_secret: str, redirect_uri: str,
                 pubsub_topic: str, token_store: GmailSecretStore):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.pubsub_topic = pubsub_topic
        self.token_store = token_store

    def authorization_url(self, state: str) -> str:
        query = urllib.parse.urlencode({
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        })
        return "https://accounts.google.com/o/oauth2/v2/auth?" + query

    def exchange_code(self, code: str) -> GmailTokenExchange:
        body = urllib.parse.urlencode({
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }).encode("utf-8")
        raw = self._request_json(
            "https://oauth2.googleapis.com/token",
            method="POST",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        refresh = str(raw.get("refresh_token") or "")
        token = str(raw.get("access_token") or "")
        if not token or not refresh:
            raise GmailProviderError("Google OAuth response is missing required tokens")
        scopes = str(raw.get("scope") or "").split()
        if not set(GMAIL_SCOPES).issubset(set(scopes)):
            raise GmailProviderError("Required Gmail scopes were not granted")
        return GmailTokenExchange(
            access_token=token,
            refresh_token=refresh,
            scope=scopes,
            expires_in=int(raw.get("expires_in") or 0),
        )

    def refresh_access_token(self, secret_resource: str) -> str:
        refresh_token = self.token_store.get_refresh_token(secret_resource)
        body = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        raw = self._request_json(
            "https://oauth2.googleapis.com/token",
            method="POST",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = str(raw.get("access_token") or "")
        if not token:
            raise GmailProviderError("Unable to refresh Gmail access token")
        return token

    def profile(self, access_token: str) -> GmailProfile:
        raw = self._gmail_json("GET", "/gmail/v1/users/me/profile", access_token)
        return GmailProfile(
            email_address=str(raw.get("emailAddress") or "").lower(),
            history_id=str(raw.get("historyId")) if raw.get("historyId") is not None else None,
        )

    def start_watch(self, access_token: str) -> GmailWatch:
        raw = self._gmail_json(
            "POST",
            "/gmail/v1/users/me/watch",
            access_token,
            {"topicName": self.pubsub_topic, "labelIds": ["INBOX"], "labelFilterBehavior": "INCLUDE"},
        )
        history_id = str(raw.get("historyId") or "")
        expiration_ms = int(raw.get("expiration") or 0)
        if not history_id or expiration_ms <= 0:
            raise GmailProviderError("Gmail watch response is incomplete")
        expiration = datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
        return GmailWatch(history_id=history_id, expiration=expiration)

    def send_message(self, access_token: str, *, to_address: str, subject: str | None,
                     body_text: str, thread_id: str | None = None) -> GmailSendReceipt:
        headers = [
            f"To: {to_address}",
            f"Subject: {subject or ''}",
            "Content-Type: text/plain; charset=UTF-8",
            "Content-Transfer-Encoding: 8bit",
            "",
            body_text,
        ]
        raw_message = "\r\n".join(headers).encode("utf-8")
        encoded = base64.urlsafe_b64encode(raw_message).decode("ascii").rstrip("=")
        payload = {"raw": encoded}
        if thread_id:
            payload["threadId"] = thread_id
        raw = self._gmail_json(
            "POST", "/gmail/v1/users/me/messages/send", access_token, payload
        )
        message_id = str(raw.get("id") or "")
        if not message_id:
            raise GmailProviderError("Gmail send response is missing message id")
        return GmailSendReceipt(
            message_id=message_id,
            thread_id=str(raw.get("threadId")) if raw.get("threadId") else None,
        )

    def list_history(self, access_token: str, start_history_id: str) -> dict:
        path = "/gmail/v1/users/me/history?" + urllib.parse.urlencode({
            "startHistoryId": start_history_id,
            "historyTypes": "messageAdded",
        })
        return self._gmail_json("GET", path, access_token)

    def get_message(self, access_token: str, message_id: str) -> dict:
        path = "/gmail/v1/users/me/messages/" + urllib.parse.quote(message_id, safe="") + "?" + urllib.parse.urlencode({
            "format": "full",
        })
        return self._gmail_json("GET", path, access_token)

    def _gmail_json(self, method: str, path: str, access_token: str, payload: dict | None = None) -> dict:
        return self._request_json(
            "https://gmail.googleapis.com" + path,
            method=method,
            body=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

    @staticmethod
    def _request_json(url: str, *, method: str, body: bytes | None = None,
                      headers: dict[str, str] | None = None) -> dict:
        request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(2 * 1024 * 1024)
        except Exception as exc:
            raise GmailProviderError("Gmail provider request failed") from exc
        try:
            value = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise GmailProviderError("Gmail provider returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise GmailProviderError("Gmail provider returned invalid response")
        return value


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)
