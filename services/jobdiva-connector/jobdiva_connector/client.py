from __future__ import annotations

from typing import Any

import httpx

from .config import JobDivaSettings


class JobDivaContractNotConfigured(RuntimeError):
    pass


class JobDivaClient:
    """Thin JobDiva transport.

    Authentication and concrete endpoint paths are intentionally not guessed.
    Add them only after JobDiva provides the V2 method/authentication contract.
    """

    def __init__(self, settings: JobDivaSettings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url.rstrip("/"),
            timeout=settings.request_timeout_seconds,
        )
        self._access_token: str | None = None

    async def close(self) -> None:
        await self._client.aclose()

    async def authenticate(self) -> str:
        raise JobDivaContractNotConfigured(
            "JobDiva authentication contract is pending official V2 documentation."
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers: dict[str, str] = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        response = await self._client.request(
            method,
            path,
            params=params,
            json=json,
            headers=headers,
        )
        response.raise_for_status()
        return response

    async def list_jobs(self, *, updated_since: str | None = None) -> list[dict[str, Any]]:
        raise JobDivaContractNotConfigured(
            "Job listing endpoint is pending official V2 method documentation."
        )

    async def list_candidates(self, *, updated_since: str | None = None) -> list[dict[str, Any]]:
        raise JobDivaContractNotConfigured(
            "Candidate endpoint is pending official V2 method documentation."
        )

    async def get_resume(self, candidate_id: str) -> dict[str, Any]:
        raise JobDivaContractNotConfigured(
            "Resume endpoint is pending official V2 method documentation."
        )
