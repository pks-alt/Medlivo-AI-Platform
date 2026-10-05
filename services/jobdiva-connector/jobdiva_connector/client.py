"""Read-only JobDiva pilot client. No API route, database write or bulk crawler.

Use one instance in one pilot process. Quotas are local, not distributed.
The low-level transport avoids AsyncClient's INFO log of authentication URLs.
Do not enable wire-level tracing or record request bodies/query strings.
"""
from __future__ import annotations
import asyncio
import json
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, AsyncIterator, Callable
import httpx
from .config import JobDivaSettings
from .contracts import ContractError, JobDivaContract, READ_OPERATIONS


class JobDivaError(RuntimeError):
    """Safe to report: never contains request URLs, payloads or credentials."""


class JobDivaContractNotConfigured(JobDivaError):
    pass


class JobDivaHTTPError(JobDivaError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"JobDiva request failed (HTTP {status_code})")


@dataclass(repr=False)
class _Reply:
    status: int
    body: bytes = field(repr=False)
    retry_after: str | None = None


class PilotBudget:
    """Rolling minute/day budget for ALL requests, including auth and retries."""
    def __init__(self, minute: int, day: int, clock=time.monotonic, sleep=asyncio.sleep):
        self.minute, self.day, self.clock, self.sleep = minute, day, clock, sleep
        self._times: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = self.clock()
            while self._times and self._times[0] <= now - 86400:
                self._times.popleft()
            if len(self._times) >= self.day:
                raise JobDivaError("Local daily pilot budget exhausted; do not restart to bypass it")
            recent = [t for t in self._times if t > now - 60]
            if len(recent) >= self.minute:
                await self.sleep(max(0, recent[-self.minute] + 60 - now))
            self._times.append(self.clock())


def _select(value: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise JobDivaError("Response does not match the reviewed JSON wrapper")
        value = value[key]
    return value


def _ids(values: list[str | int]) -> list[str]:
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ContractError("Source IDs must be positive integer values")
        text = str(value)
        if not text.isascii() or not text.isdigit() or int(text) <= 0:
            raise ContractError("Source IDs must be positive integer values")
        result.append(str(int(text)))
    return list(dict.fromkeys(result))


class JobDivaClient:
    def __init__(self, settings: JobDivaSettings, contract: JobDivaContract | None = None,
                 *, transport: httpx.AsyncBaseTransport | None = None,
                 clock: Callable[[], float] = time.monotonic, sleep=asyncio.sleep):
        if not settings.live_enabled:
            raise JobDivaError("JobDiva live reads are disabled")
        if contract is None or not contract.reviewed:
            raise JobDivaContractNotConfigured("Review the official request contract before enabling reads")
        if contract.purpose == "test" and not isinstance(transport, httpx.MockTransport):
            raise JobDivaError("Synthetic test contracts cannot use a live transport")
        # Copy validated configuration so outside mutation cannot redirect credentials.
        self.settings = JobDivaSettings.model_validate(settings.model_dump())
        self.contract = JobDivaContract.model_validate(contract.model_dump())
        self._transport = transport if transport is not None else httpx.AsyncHTTPTransport(retries=0)
        self._clock, self._sleep = clock, sleep
        self._budget = PilotBudget(settings.requests_per_minute, settings.requests_per_day, clock, sleep)
        self._token: str | None = None
        self._token_until = 0.0
        self._auth_lock = asyncio.Lock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        self._token = None
        await self._transport.aclose()

    async def _exchange(self, method: str, path: str, location: str,
                        payload: dict[str, Any], headers: dict[str, str]) -> _Reply:
        await self._budget.acquire()
        args = { {"query": "params", "json": "json", "form": "data"}[location]: payload }
        timeout = self.settings.request_timeout_seconds
        request = httpx.Request(method, self.settings.api_base_url + path, headers=headers,
                                extensions={"timeout": dict.fromkeys(("connect", "read", "write", "pool"), timeout)}, **args)
        try:
            # Total request deadline also covers a server that trickles data indefinitely.
            async with asyncio.timeout(timeout):
                response = await self._transport.handle_async_request(request)
                try:
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self.settings.max_response_bytes:
                            raise JobDivaError("JobDiva response exceeds the pilot size limit")
                        chunks.append(chunk)
                    return _Reply(response.status_code, b"".join(chunks), response.headers.get("Retry-After"))
                finally:
                    await response.aclose()
        except (httpx.TransportError, TimeoutError):
            raise JobDivaError("JobDiva network request failed or timed out") from None

    def _retry_delay(self, value: str | None, attempt: int) -> float:
        if value:
            try:
                delay = float(value)
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(value)
                    delay = (parsed - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    delay = 2 ** attempt
            if not (delay < float("inf")) or delay > 60:
                # Never shorten a vendor's longer Retry-After and retry too early.
                raise JobDivaError("JobDiva requested a longer pause; stop and reschedule the pilot")
            return max(0, delay)
        return float(2 ** attempt)

    async def _send(self, method: str, path: str, location: str,
                    payload: dict[str, Any], headers: dict[str, str]) -> _Reply:
        for attempt in range(3):
            reply = await self._exchange(method, path, location, payload, headers)
            if reply.status not in {429, 500, 502, 503, 504} or attempt == 2:
                return reply
            await self._sleep(self._retry_delay(reply.retry_after, attempt))
        raise AssertionError("unreachable")

    async def authenticate(self) -> None:
        """Cache credentials server-side; deliberately do not return the token."""
        async with self._auth_lock:
            if self._token and self._clock() < self._token_until:
                return
            auth = self.contract.authentication
            payload = {
                auth.client_id_parameter: int(self.settings.client_id),
                auth.username_parameter: self.settings.username.get_secret_value(),
                auth.password_parameter: self.settings.password.get_secret_value(),
            }
            reply = await self._send(auth.method, auth.path, auth.location, payload, {"Accept": "application/json"})
            if not 200 <= reply.status < 300:
                raise JobDivaHTTPError(reply.status)
            try:
                value = json.loads(reply.body)
            except (ValueError, UnicodeDecodeError):
                value = reply.body.decode("utf-8", errors="replace").strip()
            token = _select(value, auth.token_path)
            if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token) or len(token) > 16384:
                raise JobDivaError("Authentication did not return the expected JWT")
            self._token = token
            # JobDiva support specifies a 24-hour token; refresh five minutes early.
            self._token_until = self._clock() + 86400 - 300

    async def read_records(self, operation: str, *, ids: list[str | int] | None = None,
                           parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if operation not in READ_OPERATIONS or operation not in self.contract.operations:
            raise ContractError("Only configured read-only pilot operations are allowed")
        spec = self.contract.operations[operation]
        payload = dict(parameters or {})
        if set(payload) - set(spec.parameters):
            raise ContractError("Undeclared request parameter; review Swagger before use")
        if set(spec.required_parameters) - set(payload):
            raise ContractError("A required reviewed parameter is missing")
        if spec.ids_parameter:
            clean = _ids(ids or [])
            if not clean or len(clean) > spec.max_ids:
                raise ContractError("Supply between 1 and the reviewed maximum of 100 IDs")
            values = [int(i) for i in clean] if spec.id_value_type == "integer" else clean
            payload[spec.ids_parameter] = ",".join(clean) if spec.id_encoding == "csv" else values
        elif ids is not None:
            raise ContractError("This operation does not accept IDs")
        for attempt in range(2):
            await self.authenticate()
            token = self._token
            assert token is not None
            headers = {"Accept": "application/json", "Authorization": self.contract.authentication.authorization_prefix + token}
            reply = await self._send(spec.method, spec.path, spec.location, payload, headers)
            if reply.status == 401 and attempt == 0:
                # Avoid invalidating a token another coroutine has already refreshed.
                if self._token == token:
                    self._token = None
                continue
            if not 200 <= reply.status < 300:
                raise JobDivaHTTPError(reply.status)
            try:
                value = _select(json.loads(reply.body), spec.records_path)
            except (ValueError, UnicodeDecodeError):
                raise JobDivaError("JobDiva response is not valid JSON") from None
            if not isinstance(value, list) or any(not isinstance(record, dict) for record in value):
                raise JobDivaError("JobDiva response does not match the reviewed record array")
            return value
        raise JobDivaError("JobDiva authentication failed after one refresh")

    async def read_batches(self, operation: str, ids: list[str | int], *,
                           parameters: dict[str, Any] | None = None) -> AsyncIterator[list[dict[str, Any]]]:
        if operation not in self.contract.operations or not self.contract.operations[operation].ids_parameter:
            raise ContractError("Batch reads require an approved ID-based operation")
        clean = _ids(ids)
        size = self.contract.operations[operation].max_ids
        for offset in range(0, len(clean), size):
            yield await self.read_records(operation, ids=clean[offset:offset + size], parameters=parameters)
