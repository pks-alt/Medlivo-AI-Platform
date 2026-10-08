"""Safe manual connectivity probe for the Medlivo JobDiva integration.

Requires JOBDIVA_CLIENT_ID, JOBDIVA_USERNAME, and JOBDIVA_PASSWORD.
Prints only connection status, record count, and non-sensitive job identifiers/titles.
"""
from __future__ import annotations

import asyncio
from typing import Any

from jobdiva_connector.client import JobDivaClient, JobDivaError
from jobdiva_connector.config import JobDivaSettings


def safe_job_summary(row: dict[str, Any]) -> dict[str, Any]:
    def first(*names: str):
        for name in names:
            if name in row and row[name] not in (None, ""):
                return row[name]
        return None
    return {
        "id": first("id", "ID", "jobId", "JOBID", "jobid"),
        "title": first("title", "TITLE", "jobTitle", "JOBTITLE"),
        "status": first("status", "STATUS", "jobStatus", "JOBSTATUS"),
    }


async def main() -> int:
    settings = JobDivaSettings()
    try:
        async with JobDivaClient(settings) as client:
            await client.authenticate()
            print("JobDiva authentication: OK")
            jobs = await client.open_jobs()
            print(f"OpenJobsList records received: {len(jobs)}")
            for row in jobs[:5]:
                print(safe_job_summary(row))
        return 0
    except (JobDivaError, Exception) as exc:
        # Never print settings, credentials, token, response body, or request URL
        # because auth credentials are query parameters in JobDiva's contract.
        print(f"JobDiva probe failed: {type(exc).__name__}: {str(exc)[:240]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
