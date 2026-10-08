from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from .config import JobDivaSettings


class JobDivaError(RuntimeError):
    pass


class JobDivaClient:
    """Read-only JobDiva V2 client for Medlivo Phase 1."""

    AUTH_PATH = "/apiv2/v2/authenticate"
    OPEN_JOBS_PATH = "/apiv2/bi/OpenJobsList"
    UPDATED_JOBS_PATH = "/apiv2/bi/NewUpdatedJobRecords"
    UPDATED_CANDIDATES_PATH = "/apiv2/bi/NewUpdatedCandidateRecords"
    CANDIDATE_PROFILE_PATH = "/apiv2/bi/CandidatesProfileDetail"
    CANDIDATE_LICENSES_PATH = "/apiv2/bi/CandidatesLicensesDetail"
    CANDIDATE_CERTIFICATIONS_PATH = "/apiv2/bi/CandidatesCertificationsDetails"
    CANDIDATE_RESUMES_PATH = "/apiv2/bi/CandidatesResumesDetail"
    RESUME_TEXT_PATH = "/apiv2/bi/ResumesTextDetail"
    DATE_FORMAT = "%m/%d/%Y %H:%M:%S"

    def __init__(
        self,
        settings: JobDivaSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url,
            timeout=settings.request_timeout_seconds,
            transport=transport,
            follow_redirects=False,
        )
        self._access_token: str | None = None

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "JobDivaClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    @staticmethod
    def _extract_token(response: httpx.Response) -> str:
        raw = response.text.strip()
        if not raw:
            raise JobDivaError("JobDiva authentication returned an empty token")
        # JobDiva documents a string response. Accept either plain text or a
        # JSON-encoded string without logging or exposing the value.
        if raw.startswith('"') and raw.endswith('"'):
            try:
                value = response.json()
            except ValueError as exc:
                raise JobDivaError("JobDiva authentication returned an invalid token") from exc
            if not isinstance(value, str):
                raise JobDivaError("JobDiva authentication returned an unexpected payload")
            raw = value.strip()
        if any(ch.isspace() for ch in raw) or len(raw) < 8 or len(raw) > 8192:
            raise JobDivaError("JobDiva authentication returned an invalid token")
        return raw

    async def authenticate(self) -> str:
        response = await self._client.get(
            self.AUTH_PATH,
            params={
                "clientid": self.settings.client_id,
                "username": self.settings.username,
                "password": self.settings.password,
            },
            headers={"Accept": "application/json"},
        )
        if response.status_code in {401, 403}:
            raise JobDivaError("JobDiva rejected the API credentials or permissions")
        response.raise_for_status()
        self._access_token = self._extract_token(response)
        return self._access_token

    def _authorization_value(self) -> str:
        if not self._access_token:
            raise JobDivaError("Authenticate before calling JobDiva data endpoints")
        prefix = self.settings.authorization_prefix
        return f"{prefix} {self._access_token}".strip()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        if method.upper() != "GET":
            raise JobDivaError("Phase 1 JobDiva connector is read-only")
        response = await self._client.request(
            "GET",
            path,
            params=params,
            headers={
                "Accept": "application/json",
                "Authorization": self._authorization_value(),
            },
        )
        if response.status_code == 401:
            # One controlled re-authentication handles token expiry without
            # retrying arbitrary mutations. Phase 1 has GET endpoints only.
            await self.authenticate()
            response = await self._client.request(
                "GET",
                path,
                params=params,
                headers={
                    "Accept": "application/json",
                    "Authorization": self._authorization_value(),
                },
            )
        response.raise_for_status()
        return response

    @staticmethod
    def _json_records(response: httpx.Response) -> list[dict[str, Any]]:
        try:
            value = response.json()
        except ValueError as exc:
            raise JobDivaError("JobDiva returned non-JSON data") from exc
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            for key in ("data", "records", "items", "results"):
                rows = value.get(key)
                if isinstance(rows, list):
                    return [row for row in rows if isinstance(row, dict)]
        raise JobDivaError("JobDiva returned an unexpected record payload")

    async def open_jobs(self) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.OPEN_JOBS_PATH))

    async def updated_jobs(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        page_number: int = 1,
        page_size: int = 25,
    ) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.UPDATED_JOBS_PATH, params={
            "fromDate": from_date.strftime(self.DATE_FORMAT),
            "toDate": to_date.strftime(self.DATE_FORMAT),
            "pageNumber": page_number,
            "pageSize": page_size,
        }))

    async def updated_candidates(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        page_number: int = 1,
        page_size: int = 25,
    ) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.UPDATED_CANDIDATES_PATH, params={
            "fromDate": from_date.strftime(self.DATE_FORMAT),
            "toDate": to_date.strftime(self.DATE_FORMAT),
            "pageNumber": page_number,
            "pageSize": page_size,
        }))


    async def candidate_profile(self, candidate_id: str | int) -> list[dict[str, Any]]:
        """Fetch the authoritative JobDiva candidate profile detail.

        The connector remains read-only. Query naming follows JobDiva's BI V2
        convention and is isolated here so live source validation can adjust it
        without changing Candidate Intelligence.
        """
        return self._json_records(await self.request(
            "GET", self.CANDIDATE_PROFILE_PATH, params={"candidateId": candidate_id}
        ))

    async def candidate_licenses(self, candidate_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request(
            "GET", self.CANDIDATE_LICENSES_PATH, params={"candidateId": candidate_id}
        ))

    async def candidate_certifications(self, candidate_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request(
            "GET", self.CANDIDATE_CERTIFICATIONS_PATH, params={"candidateId": candidate_id}
        ))

    async def candidate_resumes(self, candidate_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request(
            "GET", self.CANDIDATE_RESUMES_PATH, params={"candidateId": candidate_id}
        ))

    async def resume_text(self, resume_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request(
            "GET", self.RESUME_TEXT_PATH, params={"resumeId": resume_id}
        ))
