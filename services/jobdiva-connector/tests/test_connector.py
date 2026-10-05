"""Synthetic request contracts only. No vendor schema or live records in fixtures."""
import asyncio
import copy
import io
import json
import logging
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from jobdiva_connector.client import JobDivaClient, JobDivaError, JobDivaHTTPError, PilotBudget
from jobdiva_connector.config import JobDivaSettings
from jobdiva_connector.contracts import ContractError, JobDivaContract
from jobdiva_connector.resumes import latest_resume_id
from jobdiva_connector.__main__ import run

# All names/serialization/wrappers here are TEST assumptions, not vendor verification.
CONTRACT = {
    "purpose": "test", "reviewed": True, "evidence": "SYNTHETIC UNIT TEST ONLY: not a live API contract",
    "authentication": {"path": "/api/authenticate", "method": "GET", "location": "query",
        "client_id_parameter": "clientid", "username_parameter": "username",
        "password_parameter": "password", "authorization_prefix": "Bearer "},
    "operations": {
        "JobsDetail": {"path": "/apiv2/bi/JobsDetail", "method": "GET", "location": "query", "ids_parameter": "jobIds"},
        "CandidatesProfileDetail": {"path": "/apiv2/bi/CandidatesProfileDetail", "method": "POST", "location": "json",
            "ids_parameter": "candidateIds", "id_encoding": "json", "records_path": ["records"], "parameters": ["userFieldsName"]},
        "CandidatesResumesDetail": {"path": "/apiv2/bi/CandidatesResumesDetail", "method": "GET", "location": "query", "ids_parameter": "candidateIds"},
        "ResumesTextDetail": {"path": "/apiv2/bi/ResumesTextDetail", "method": "GET", "location": "query", "ids_parameter": "resumeIds"},
    },
}
TOKEN = "synthetic.payload.signature"


class Clock:
    def __init__(self): self.now, self.sleeps = 0.0, []
    def __call__(self): return self.now
    async def sleep(self, seconds): self.sleeps.append(seconds); self.now += seconds


def settings(**overrides):
    return JobDivaSettings(live_enabled=True, client_id="999999", username="test-only-user",
                          password="test-only-password", api_base_url="https://api.jobdiva.com", **overrides)


class ConfigTests(unittest.TestCase):
    def test_disabled_settings_need_no_secrets(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(JobDivaSettings().live_enabled)

    def test_disabled_client_never_connects(self):
        with self.assertRaisesRegex(JobDivaError, "disabled"):
            JobDivaClient(JobDivaSettings(live_enabled=False))

    def test_missing_review_blocks_client(self):
        with self.assertRaisesRegex(JobDivaError, "Review"):
            JobDivaClient(settings())
        data = copy.deepcopy(CONTRACT); data["reviewed"] = False
        with self.assertRaises(JobDivaError):
            JobDivaClient(settings(), JobDivaContract.model_validate(data))

    def test_synthetic_contract_cannot_connect_live(self):
        with self.assertRaisesRegex(JobDivaError, "Synthetic test contracts"):
            JobDivaClient(settings(), JobDivaContract.model_validate(CONTRACT))

    def test_credentials_are_redacted_from_repr(self):
        text = repr(settings())
        self.assertNotIn("test-only-password", text)
        self.assertNotIn("test-only-user", text)

    def test_untrusted_destinations_rejected(self):
        for url in ["http://api.jobdiva.com", "https://attacker.example", "https://api.jobdiva.com.evil.example",
                    "https://user:pass@api.jobdiva.com", "https://api.jobdiva.com:444", "https://api.jobdiva.com/path",
                    "https://api.jobdiva.com/?token=secret", "https://api.jobdiva.com/#part"]:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                JobDivaSettings(**{**settings().model_dump(), "api_base_url": url})

    def test_write_endpoint_cannot_be_disguised_as_read(self):
        data = copy.deepcopy(CONTRACT); data["operations"]["JobsDetail"]["path"] = "/apiv2/jobdiva/updateCandidateProfile"
        with self.assertRaises(ValidationError): JobDivaContract.model_validate(data)

    def test_detail_operation_cannot_omit_ids(self):
        data = copy.deepcopy(CONTRACT); data["operations"]["JobsDetail"].pop("ids_parameter")
        with self.assertRaises(ValidationError): JobDivaContract.model_validate(data)

    def test_mismatched_operation_rejected(self):
        data = copy.deepcopy(CONTRACT); data["operations"]["JobsDetail"]["path"] = "/apiv2/bi/ResumesTextDetail"
        with self.assertRaises(ValidationError): JobDivaContract.model_validate(data)

    def test_redirect_auth_endpoint_not_allowed(self):
        data = copy.deepcopy(CONTRACT); data["authentication"]["path"] = "//attacker.example/authenticate"
        with self.assertRaises(ValidationError): JobDivaContract.model_validate(data)

    def test_get_json_contract_rejected(self):
        data = copy.deepcopy(CONTRACT); data["authentication"]["location"] = "json"
        with self.assertRaises(ValidationError): JobDivaContract.model_validate(data)


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self): self.clients, self.calls, self.clock = [], [], Clock()
    async def asyncTearDown(self):
        for client in self.clients: await client.close()

    def client(self, handler=None, contract=None, **config):
        async def send(request):
            self.calls.append(request)
            if handler: return await handler(request)
            if request.url.path.endswith("authenticate"): return httpx.Response(200, json=TOKEN)
            if request.url.path.endswith("CandidatesProfileDetail"): return httpx.Response(200, json={"records": [{"id": "1"}]})
            return httpx.Response(200, json=[{"id": "1"}])
        client = JobDivaClient(settings(**config), JobDivaContract.model_validate(contract or CONTRACT),
                              transport=httpx.MockTransport(send), clock=self.clock, sleep=self.clock.sleep)
        self.clients.append(client)
        return client

    async def test_token_cached_and_only_sent_to_reads(self):
        client = self.client()
        self.assertEqual(await client.read_records("JobsDetail", ids=[1]), [{"id": "1"}])
        await client.read_records("JobsDetail", ids=[2])
        self.assertEqual(len(self.calls), 3)
        self.assertNotIn("Authorization", self.calls[0].headers)
        self.assertEqual(self.calls[1].headers["Authorization"], f"Bearer {TOKEN}")
        self.assertNotIn("password", self.calls[1].url.params)
        self.assertIsNone(await client.authenticate())

    async def test_plain_text_token_supported(self):
        async def handler(r):
            return httpx.Response(200, text=TOKEN) if r.url.path.endswith("authenticate") else httpx.Response(200, json=[])
        self.assertEqual(await self.client(handler).read_records("JobsDetail", ids=[1]), [])

    async def test_concurrent_calls_share_authentication(self):
        client = self.client()
        await asyncio.gather(client.read_records("JobsDetail", ids=[1]), client.read_records("JobsDetail", ids=[2]))
        self.assertEqual(sum(r.url.path.endswith("authenticate") for r in self.calls), 1)

    async def test_early_token_refresh(self):
        client = self.client(); await client.read_records("JobsDetail", ids=[1])
        self.clock.now += 86400 - 300
        await client.read_records("JobsDetail", ids=[1])
        self.assertEqual(sum(r.url.path.endswith("authenticate") for r in self.calls), 2)

    async def test_401_refresh_once(self):
        reads = 0
        async def handler(r):
            nonlocal reads
            if r.url.path.endswith("authenticate"): return httpx.Response(200, json=TOKEN)
            reads += 1
            return httpx.Response(401, text="sensitive") if reads == 1 else httpx.Response(200, json=[])
        await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertEqual(len(self.calls), 4)

    async def test_repeated_401_stops(self):
        async def handler(r):
            return httpx.Response(200, json=TOKEN) if r.url.path.endswith("authenticate") else httpx.Response(401, text="secret response")
        with self.assertRaisesRegex(JobDivaHTTPError, "HTTP 401"):
            await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertEqual(len(self.calls), 4)

    async def test_403_not_retried(self):
        async def handler(r): return httpx.Response(403, text="private candidate details")
        with self.assertRaisesRegex(JobDivaHTTPError, "HTTP 403") as error:
            await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertNotIn("private", str(error.exception)); self.assertEqual(len(self.calls), 1)

    async def test_redirect_not_followed(self):
        async def handler(r): return httpx.Response(302, headers={"Location": "https://attacker.example"})
        with self.assertRaisesRegex(JobDivaHTTPError, "HTTP 302"):
            await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertEqual(len(self.calls), 1)

    async def test_http_info_logging_does_not_expose_auth_query(self):
        log = io.StringIO(); handler = logging.StreamHandler(log); logger = logging.getLogger("httpx")
        level = logger.level; logger.addHandler(handler); logger.setLevel(logging.INFO)
        try: await self.client().read_records("JobsDetail", ids=[1])
        finally: logger.removeHandler(handler); logger.setLevel(level)
        self.assertNotIn("test-only-password", log.getvalue()); self.assertNotIn(TOKEN, log.getvalue())

    async def test_invalid_ids_rejected_before_network(self):
        client = self.client()
        for ids in [[], [True], [-1], ["1,2"], [1.5], [""], ["١"], list(range(1, 102))]:
            with self.subTest(ids=ids), self.assertRaises(ContractError): await client.read_records("JobsDetail", ids=ids)
        self.assertEqual(self.calls, [])

    async def test_batching_deduplicates_and_caps_at_100(self):
        client = self.client()
        batches = [b async for b in client.read_batches("JobsDetail", [*range(1, 206), 1])]
        self.assertEqual(len(batches), 3)
        lengths = [len(r.url.params["jobIds"].split(",")) for r in self.calls[1:]]
        self.assertEqual(lengths, [100, 100, 5])

    async def test_unknown_and_write_operations_blocked(self):
        client = self.client()
        for name in ["createSubmittal", "updateCandidateProfile", "ResumeDetail", "Unknown"]:
            with self.assertRaises(ContractError): await client.read_records(name, ids=[1])
        self.assertEqual(self.calls, [])

    async def test_undeclared_parameters_blocked(self):
        with self.assertRaises(ContractError): await self.client().read_records("JobsDetail", ids=[1], parameters={"unknown": "value"})
        self.assertEqual(self.calls, [])

    async def test_post_is_allowed_only_for_reviewed_read(self):
        await self.client().read_records("CandidatesProfileDetail", ids=[1, 2], parameters={"userFieldsName": ["TEST_FIELD"]})
        self.assertEqual(self.calls[1].method, "POST")
        self.assertEqual(json.loads(self.calls[1].content), {"candidateIds": [1, 2], "userFieldsName": ["TEST_FIELD"]})

    async def test_malformed_response_is_sanitized(self):
        async def handler(r):
            return httpx.Response(200, json=TOKEN) if r.url.path.endswith("authenticate") else httpx.Response(200, text="private HTML")
        with self.assertRaisesRegex(JobDivaError, "not valid JSON"):
            await self.client(handler).read_records("JobsDetail", ids=[1])

    async def test_object_instead_of_array_rejected(self):
        async def handler(r):
            return httpx.Response(200, json=TOKEN) if r.url.path.endswith("authenticate") else httpx.Response(200, json={"error": "private"})
        with self.assertRaisesRegex(JobDivaError, "record array"):
            await self.client(handler).read_records("JobsDetail", ids=[1])

    async def test_invalid_token_blocks_data_call(self):
        async def handler(r): return httpx.Response(200, json={"error": "no token"})
        with self.assertRaisesRegex(JobDivaError, "expected JWT"):
            await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertEqual(len(self.calls), 1)

    async def test_network_errors_hide_url(self):
        async def handler(r): raise httpx.ConnectError("password=test-only-password", request=r)
        with self.assertRaises(JobDivaError) as error:
            await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertNotIn("password", str(error.exception)); self.assertIsNone(error.exception.__cause__)

    async def test_large_response_stops(self):
        async def handler(r): return httpx.Response(200, content=b"x" * 101)
        with self.assertRaisesRegex(JobDivaError, "size limit"):
            await self.client(handler, max_response_bytes=100).read_records("JobsDetail", ids=[1])

    async def test_429_respects_retry_after(self):
        n = 0
        async def handler(r):
            nonlocal n
            n += 1
            if n == 1: return httpx.Response(429, headers={"Retry-After": "7"})
            return httpx.Response(200, json=TOKEN) if r.url.path.endswith("authenticate") else httpx.Response(200, json=[])
        await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertEqual(self.clock.sleeps, [7])

    async def test_long_retry_after_not_shortened(self):
        async def handler(r): return httpx.Response(429, headers={"Retry-After": "3600"})
        with self.assertRaisesRegex(JobDivaError, "longer pause"):
            await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertEqual(self.clock.sleeps, []); self.assertEqual(len(self.calls), 1)

    async def test_503_has_bounded_retries(self):
        async def handler(r): return httpx.Response(503)
        with self.assertRaisesRegex(JobDivaHTTPError, "HTTP 503"):
            await self.client(handler).read_records("JobsDetail", ids=[1])
        self.assertEqual(len(self.calls), 3); self.assertEqual(self.clock.sleeps, [1, 2])

    async def test_minute_budget_accounts_for_all_requests(self):
        clock = Clock(); budget = PilotBudget(2, 1000, clock, clock.sleep)
        await budget.acquire(); await budget.acquire(); await budget.acquire()
        self.assertEqual(clock.sleeps, [60])

    async def test_daily_budget_stops(self):
        clock = Clock(); budget = PilotBudget(6, 2, clock, clock.sleep)
        await budget.acquire(); await budget.acquire()
        with self.assertRaisesRegex(JobDivaError, "daily pilot budget"): await budget.acquire()

    async def test_dry_run_needs_no_credentials_and_calls_no_network(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict("os.environ", {}, clear=True):
            root = Path(folder); (root / "contract.json").write_text(json.dumps(CONTRACT)); (root / "ids.json").write_text("[1,2]")
            args = Namespace(contract=root / "contract.json", ids_file=root / "ids.json", parameters_file=None,
                             operation="JobsDetail", execute=False)
            with patch("httpx.AsyncHTTPTransport.handle_async_request", side_effect=AssertionError("No live request")):
                result = await run(args)
            self.assertEqual(result["mode"], "dry_run"); self.assertEqual(result["requested_ids"], 2)
            self.assertNotIn("returned_records", result)


class ResumeTests(unittest.TestCase):
    def test_select_latest_not_first(self):
        self.assertEqual(latest_resume_id([{"RESUMEID": 7, "DATECREATED": "2026-01-01T00:00:00Z"},
                                          {"RESUMEID": 8, "DATECREATED": "2026-02-01T00:00:00Z"}]), "8")
    def test_no_resume(self): self.assertIsNone(latest_resume_id([]))
    def test_naive_timestamp_requires_timezone(self):
        with self.assertRaisesRegex(ContractError, "time zone"):
            latest_resume_id([{"RESUMEID": 7, "DATECREATED": "2026-01-01T00:00:00"}])
    def test_configured_date_format(self):
        self.assertEqual(latest_resume_id([{"RESUMEID": 7, "DATECREATED": "01/02/2026 10:00:00"}],
                         date_format="%m/%d/%Y %H:%M:%S", source_timezone="UTC"), "7")
    def test_bad_or_missing_date_requires_review(self):
        for value in [None, "not a date"]:
            with self.assertRaises(ContractError): latest_resume_id([{"RESUMEID": 7, "DATECREATED": value}])
    def test_equal_timestamps_are_not_guessed(self):
        with self.assertRaisesRegex(ContractError, "Multiple resumes"):
            latest_resume_id([{"RESUMEID": i, "DATECREATED": "2026-01-01T00:00:00Z"} for i in [7, 8]])
    def test_dst_ambiguity_requires_review(self):
        with self.assertRaisesRegex(ContractError, "daylight-saving"):
            latest_resume_id([{"RESUMEID": 7, "DATECREATED": "2026-11-01T01:30:00"}], source_timezone="America/Los_Angeles")


if __name__ == "__main__": unittest.main()
