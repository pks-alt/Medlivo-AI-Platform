import pytest

from jobdiva_sync.active_job_sample import collect_active_jobs_by_division, persist_active_job_sample


def job(job_id, title, profession, specialty=None):
    value={"JOBID": job_id, "JOBTITLE": title, "PROFESSION": profession, "STATUS": "Open"}
    if specialty:
        value["SPECIALTY"]=specialty
    return value


class FakeClient:
    def __init__(self, records):
        self.records=records
    async def open_jobs(self):
        return self.records


@pytest.mark.asyncio
async def test_collects_separate_division_quotas_without_padding():
    rows=[
        job(1,"Travel RN ICU","Registered Nurse","ICU"),
        job(2,"Travel RN ER","Registered Nurse","Emergency"),
        job(3,"Physical Therapist","Physical Therapist"),
        job(4,"Occupational Therapist","Occupational Therapist"),
        job(5,"Locum Urologist","Physician","Urology"),
        job(6,"Locum Hospitalist","Physician","Hospitalist"),
        job(7,"Unknown Clinical Role","Healthcare"),
    ]
    selected, summary=await collect_active_jobs_by_division(
        FakeClient(rows), per_division=2, max_scan=20
    )
    assert len(selected)==6
    assert summary.selected_counts == {
        "nursing_allied": 2,
        "rehabilitation": 2,
        "locum_tenens": 2,
    }
    assert summary.unclassified == 0


@pytest.mark.asyncio
async def test_returns_short_bucket_when_jobdiva_has_fewer_active_jobs():
    rows=[
        job(1,"Travel RN ICU","Registered Nurse","ICU"),
        job(2,"Physical Therapist","Physical Therapist"),
        job(3,"Locum Urologist","Physician","Urology"),
        job(4,"Locum Hospitalist","Physician","Hospitalist"),
    ]
    _, summary=await collect_active_jobs_by_division(
        FakeClient(rows), per_division=2, max_scan=20
    )
    assert summary.selected_counts["nursing_allied"] == 1
    assert summary.selected_counts["rehabilitation"] == 1
    assert summary.selected_counts["locum_tenens"] == 2


@pytest.mark.asyncio
async def test_persist_sample_targets_only_selected_source_ids():
    rows=[
        job(1,"Travel RN ICU","Registered Nurse","ICU"),
        job(2,"Physical Therapist","Physical Therapist"),
        job(3,"Locum Urologist","Physician","Urology"),
    ]
    calls={}

    class Store:
        async def upsert_page(self, **kwargs):
            calls["records"]=kwargs["records"]
            return len(kwargs["records"])

    class Promoter:
        async def promote_unlinked(self, **kwargs):
            calls["source_ids"]=kwargs["source_ids"]
            return {"promoted": len(kwargs["source_ids"])}

    result=await persist_active_job_sample(
        FakeClient(rows), Store(), Promoter(),
        tenant_id="tenant-1", per_division=1, max_scan=10
    )
    assert result["complete"] is True
    assert result["records_upserted"] == 3
    assert sorted(calls["source_ids"]) == ["1","2","3"]
    assert {r["_medlivo_selected_division"] for r in calls["records"]} == {
        "nursing_allied","rehabilitation","locum_tenens"
    }
