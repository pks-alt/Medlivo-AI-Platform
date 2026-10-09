from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from job_intelligence import classify_division

from .models import SyncStream
from .runner import source_id


TARGET_DIVISIONS = ("nursing_allied", "rehabilitation", "locum_tenens")


@dataclass(frozen=True)
class ActiveJobDivisionSample:
    requested_per_division: int
    selected_counts: dict[str, int]
    selected_source_ids: dict[str, list[str]]
    scanned: int
    unclassified: int
    duplicate_source_ids: int


async def collect_active_jobs_by_division(
    client,
    *,
    per_division: int = 100,
    max_scan: int = 5000,
) -> tuple[list[dict[str, Any]], ActiveJobDivisionSample]:
    """Select up to N active JobDiva jobs per Medlivo division.

    OpenJobsList is treated as the active-job inventory. Classification uses
    only explicit division/profession/specialty/title fields. Ambiguous jobs are
    left unclassified instead of guessed.
    """
    if per_division < 1 or per_division > 500:
        raise ValueError("per_division must be between 1 and 500")
    if max_scan < per_division or max_scan > 20000:
        raise ValueError("max_scan must be between per_division and 20000")

    inventory = await client.open_jobs()
    selected: dict[str, list[dict[str, Any]]] = {key: [] for key in TARGET_DIVISIONS}
    selected_ids: dict[str, list[str]] = {key: [] for key in TARGET_DIVISIONS}
    seen: set[str] = set()
    duplicate_source_ids = 0
    unclassified = 0
    scanned = 0

    for record in inventory:
        if scanned >= max_scan:
            break
        scanned += 1
        try:
            ident = source_id(SyncStream.JOBS, record)
        except ValueError:
            unclassified += 1
            continue
        if ident in seen:
            duplicate_source_ids += 1
            continue
        seen.add(ident)

        division = classify_division(record)
        if division not in selected:
            unclassified += 1
            continue
        if len(selected[division]) >= per_division:
            continue

        # Preserve the source record exactly; only add internal selection
        # metadata to the copy persisted to the staging landing table.
        item = dict(record)
        item["_medlivo_selected_division"] = division
        item["_medlivo_selection_source"] = "jobdiva_open_jobs"
        selected[division].append(item)
        selected_ids[division].append(ident)

        if all(len(selected[key]) >= per_division for key in TARGET_DIVISIONS):
            break

    flat: list[dict[str, Any]] = []
    for division in TARGET_DIVISIONS:
        flat.extend(selected[division])

    summary = ActiveJobDivisionSample(
        requested_per_division=per_division,
        selected_counts={key: len(selected[key]) for key in TARGET_DIVISIONS},
        selected_source_ids=selected_ids,
        scanned=scanned,
        unclassified=unclassified,
        duplicate_source_ids=duplicate_source_ids,
    )
    return flat, summary


async def persist_active_job_sample(
    client,
    sync_store,
    promoter,
    *,
    tenant_id: str,
    per_division: int = 100,
    max_scan: int = 5000,
) -> dict[str, Any]:
    records, sample = await collect_active_jobs_by_division(
        client,
        per_division=per_division,
        max_scan=max_scan,
    )
    upserted = await sync_store.upsert_page(
        tenant_id=tenant_id,
        source_system="jobdiva",
        stream=SyncStream.JOBS,
        records=records,
    )
    source_ids = [
        source_id
        for division in TARGET_DIVISIONS
        for source_id in sample.selected_source_ids[division]
    ]
    promotion = await promoter.promote_unlinked(
        tenant_id=tenant_id,
        stream=SyncStream.JOBS,
        limit=max(1, len(source_ids)),
        source_ids=source_ids,
    )
    return {
        "requested_per_division": sample.requested_per_division,
        "selected_counts": sample.selected_counts,
        "complete": all(
            count >= sample.requested_per_division
            for count in sample.selected_counts.values()
        ),
        "scanned": sample.scanned,
        "unclassified": sample.unclassified,
        "duplicate_source_ids": sample.duplicate_source_ids,
        "records_upserted": upserted,
        "promotion": promotion,
    }
