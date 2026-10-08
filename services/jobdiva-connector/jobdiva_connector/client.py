from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .config import JobDivaSettings


class JobDivaError(RuntimeError):
    """Safe connector error that never contains credentials or response bodies."""


class JobDivaHTTPError(JobDivaError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"JobDiva request failed (HTTP {status_code})")


class PilotBudget:
    """Per-process safety budget for all JobDiva requests, including retries."""

    def __init__(self, minute: int, day: int, *, clock=time.monotonic, sleep=asyncio.sleep):
        self.minute = minute
        self.day = day
        self.clock = clock
        self.sleep = sleep
        self._times: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = self.clock()
            while self._times and self._times[0] <= now - 86400:
                self._times.popleft()
            if len(self._times) >= self.day:
                raise JobDivaError("JobDiva daily safety budget exhausted")
            recent = [t for t in self._times if t > now - 60]
            if len(recent) >= self.minute:
                await self.sleep(max(0, recent[-self.minute] + 60 - now))
            self._times.append(self.clock())


class JobDivaClient:
    """Read-only JobDiva V2 client for Medlivo Phase 1."""

    AUTH_PATH = "/apiv2/v2/authenticate"
    OPEN_JOBS_PATH = "/apiv2/bi/OpenJobsList"
    JOB_DETAIL_PATH = "/apiv2/bi/JobsDetail"
    UPDATED_JOBS_PATH = "/apiv2/bi/NewUpdatedJobRecords"
    UPDATED_CANDIDATES_PATH = "/apiv2/bi/NewUpdatedCandidateRecords"
    CANDIDATE_PROFILE_PATH = "/apiv2/bi/CandidatesProfileDetail"
    CANDIDATE_LICENSES_PATH = "/apiv2/bi/CandidatesLicensesDetail"
    CANDIDATE_CERTIFICATIONS_PATH = "/apiv2/bi/CandidatesCertificationsDetails"
    CANDIDATE_RESUMES_PATH = "/apiv2/bi/CandidatesResumesDetail"
    RESUME_TEXT_PATH = "/apiv2/bi/ResumesTextDetail"
    DATE_FORMAT = "%m/%d/%Y %H:%M:%S"

    READ_PATHS = {
        OPEN_JOBS_PATH,
        JOB_DETAIL_PATH,
        UPDATED_JOBS_PATH,
        UPDATED_CANDIDATES_PATH,
        CANDIDATE_PROFILE_PATH,
        CANDIDATE_LICENSES_PATH,
        CANDIDATE_CERTIFICATIONS_PATH,
        CANDIDATE_RESUMES_PATH,
        RESUME_TEXT_PATH,
    }

    def __init__(
        self,
        settings: JobDivaSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        clock=time.monotonic,
        sleep=asyncio.sleep,
    ) -> None:
        if not settings.live_enabled:
            raise JobDivaError("JobDiva live reads are disabled")
        self.settings = JobDivaSettings.model_validate(settings.model_dump())
        self._sleep = sleep
        self._budget = PilotBudget(
            settings.requests_per_minute,
            settings.requests_per_day,
            clock=clock,
            sleep=sleep,
        )
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url,
            timeout=settings.request_timeout_seconds,
            transport=transport,
            follow_redirects=False,
        )
        self._access_token: str | None = None
        self._auth_lock = asyncio.Lock()

    async def close(self) -> None:
        self._access_token = None
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
        if raw.startswith('"') and raw.endswith('"'):
            try:
                value = response.json()
            except ValueError:
                raise JobDivaError("JobDiva authentication returned an invalid token") from None
            if not isinstance(value, str):
                raise JobDivaError("JobDiva authentication returned an unexpected payload")
            raw = value.strip()
        if any(ch.isspace() for ch in raw) or len(raw) < 8 or len(raw) > 8192:
            raise JobDivaError("JobDiva authentication returned an invalid token")
        return raw

    async def _bounded_request(self, method: str, path: str, *, params=None, headers=None) -> httpx.Response:
        for attempt in range(3):
            await self._budget.acquire()
            try:
                response = await self._client.request(
                    method,
                    path,
                    params=params,
                    headers=headers,
                )
            except (httpx.TransportError, TimeoutError):
                raise JobDivaError("JobDiva network request failed or timed out") from None

            body = response.content
            if len(body) > self.settings.max_response_bytes:
                raise JobDivaError("JobDiva response exceeds the configured size limit")

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = None
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        try:
                            parsed = parsedate_to_datetime(retry_after)
                            delay = max(0.0, parsed.timestamp() - datetime.now().timestamp())
                        except Exception:
                            delay = None
                if delay is None:
                    delay = float(2 ** attempt)
                if delay > self.settings.max_retry_after_seconds:
                    raise JobDivaError("JobDiva requested a longer pause than the connector allows")
                if attempt == 2:
                    raise JobDivaHTTPError(429)
                await self._sleep(delay)
                continue

            if response.status_code in {500, 502, 503, 504}:
                if attempt == 2:
                    raise JobDivaHTTPError(response.status_code)
                await self._sleep(float(2 ** attempt))
                continue

            return response

        raise JobDivaError("JobDiva request retry budget exhausted")

    async def authenticate(self) -> str:
        async with self._auth_lock:
            response = await self._bounded_request(
                "GET",
                self.AUTH_PATH,
                params={
                    "clientid": self.settings.client_id,
                    "username": self.settings.username.get_secret_value(),
                    "password": self.settings.password.get_secret_value(),
                },
                headers={"Accept": "application/json"},
            )
            if response.status_code in {401, 403}:
                raise JobDivaError("JobDiva rejected the API credentials or permissions")
            if response.status_code >= 400:
                raise JobDivaHTTPError(response.status_code)
            self._access_token = self._extract_token(response)
            return self._access_token

    def _authorization_value(self) -> str:
        if not self._access_token:
            raise JobDivaError("Authenticate before calling JobDiva data endpoints")
        prefix = self.settings.authorization_prefix
        return f"{prefix} {self._access_token}".strip()

    async def request(self, method: str, path: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        if method.upper() != "GET" or path not in self.READ_PATHS:
            raise JobDivaError("Phase 1 JobDiva connector is read-only and allowlisted")
        response = await self._bounded_request(
            "GET",
            path,
            params=params,
            headers={"Accept": "application/json", "Authorization": self._authorization_value()},
        )
        if response.status_code == 401:
            await self.authenticate()
            response = await self._bounded_request(
                "GET",
                path,
                params=params,
                headers={"Accept": "application/json", "Authorization": self._authorization_value()},
            )
        if response.status_code >= 400:
            raise JobDivaHTTPError(response.status_code)
        return response

    @staticmethod
    def _json_records(response: httpx.Response) -> list[dict[str, Any]]:
        try:
            value = response.json()
        except ValueError:
            raise JobDivaError("JobDiva returned non-JSON data") from None
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

    async def job_detail(self, job_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request(
            "GET", self.JOB_DETAIL_PATH, params={"jobId": job_id}
        ))

    async def updated_jobs(self, *, from_date: datetime, to_date: datetime, page_number: int = 1, page_size: int = 25) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.UPDATED_JOBS_PATH, params={
            "fromDate": from_date.strftime(self.DATE_FORMAT),
            "toDate": to_date.strftime(self.DATE_FORMAT),
            "pageNumber": page_number,
            "pageSize": page_size,
        }))

    async def updated_candidates(self, *, from_date: datetime, to_date: datetime, page_number: int = 1, page_size: int = 25) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.UPDATED_CANDIDATES_PATH, params={
            "fromDate": from_date.strftime(self.DATE_FORMAT),
            "toDate": to_date.strftime(self.DATE_FORMAT),
            "pageNumber": page_number,
            "pageSize": page_size,
        }))

    async def candidate_profile(self, candidate_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.CANDIDATE_PROFILE_PATH, params={"candidateId": candidate_id}))

    async def candidate_licenses(self, candidate_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.CANDIDATE_LICENSES_PATH, params={"candidateId": candidate_id}))

    async def candidate_certifications(self, candidate_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.CANDIDATE_CERTIFICATIONS_PATH, params={"candidateId": candidate_id}))

    async def candidate_resumes(self, candidate_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.CANDIDATE_RESUMES_PATH, params={"candidateId": candidate_id}))

    async def resume_text(self, resume_id: str | int) -> list[dict[str, Any]]:
        return self._json_records(await self.request("GET", self.RESUME_TEXT_PATH, params={"resumeId": resume_id}))
