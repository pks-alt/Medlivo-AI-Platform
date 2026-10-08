from datetime import datetime
import httpx
import pytest

from jobdiva_connector.client import JobDivaClient, JobDivaError
from jobdiva_connector.config import JobDivaSettings


def settings(**overrides):
    values = dict(
        client_id=2781,
        username="api-user@example.test",
        password="not-a-real-secret",
        api_base_url="https://api.jobdiva.com",
    )
    values.update(overrides)
    return JobDivaSettings(**values)


@pytest.mark.asyncio
async def test_authenticate_uses_documented_query_parameters_and_hides_token():
    seen = {}
    async def handler(request):
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, text='"synthetic-token-123"')
    client = JobDivaClient(settings(), transport=httpx.MockTransport(handler))
    try:
        token = await client.authenticate()
        assert token == "synthetic-token-123"
        assert seen["path"] == "/apiv2/v2/authenticate"
        assert seen["params"]["clientid"] == "2781"
        assert seen["params"]["username"] == "api-user@example.test"
        assert seen["params"]["password"] == "not-a-real-secret"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_open_jobs_uses_authorization_header_after_authentication():
    requests = []
    async def handler(request):
        requests.append(request)
        if request.url.path.endswith("/authenticate"):
            return httpx.Response(200, text="synthetic-token-123")
        return httpx.Response(200, json=[{"id": 1, "title": "Synthetic RN"}])
    client = JobDivaClient(settings(), transport=httpx.MockTransport(handler))
    try:
        await client.authenticate()
        rows = await client.open_jobs()
        assert rows[0]["id"] == 1
        assert requests[-1].url.path == "/apiv2/bi/OpenJobsList"
        assert requests[-1].headers["Authorization"] == "synthetic-token-123"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_phase_one_rejects_write_requests():
    client = JobDivaClient(settings(), transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    client._access_token = "synthetic-token-123"
    try:
        with pytest.raises(JobDivaError, match="read-only"):
            await client.request("POST", "/apiv2/jobdiva/createJob")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_updated_jobs_formats_dates_and_pages():
    captured = {}
    async def handler(request):
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=[])
    client = JobDivaClient(settings(), transport=httpx.MockTransport(handler))
    client._access_token = "synthetic-token-123"
    try:
        await client.updated_jobs(
            from_date=datetime(2026, 10, 1, 0, 0, 0),
            to_date=datetime(2026, 10, 7, 23, 59, 59),
            page_number=2,
            page_size=10,
        )
        assert captured["params"] == {
            "fromDate": "10/01/2026 00:00:00",
            "toDate": "10/07/2026 23:59:59",
            "pageNumber": "2",
            "pageSize": "10",
        }
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_candidate_intelligence_reads_use_candidate_and_resume_ids():
    seen = []
    async def handler(request):
        seen.append((request.url.path, dict(request.url.params)))
        return httpx.Response(200, json=[{"synthetic": True}])

    client = JobDivaClient(settings(), transport=httpx.MockTransport(handler))
    client._access_token = "synthetic-token-123"
    try:
        await client.candidate_profile(123)
        await client.candidate_licenses(123)
        await client.candidate_certifications(123)
        await client.candidate_resumes(123)
        await client.resume_text(456)

        assert seen == [
            ("/apiv2/bi/CandidatesProfileDetail", {"candidateId": "123"}),
            ("/apiv2/bi/CandidatesLicensesDetail", {"candidateId": "123"}),
            ("/apiv2/bi/CandidatesCertificationsDetails", {"candidateId": "123"}),
            ("/apiv2/bi/CandidatesResumesDetail", {"candidateId": "123"}),
            ("/apiv2/bi/ResumesTextDetail", {"resumeId": "456"}),
        ]
    finally:
        await client.close()
