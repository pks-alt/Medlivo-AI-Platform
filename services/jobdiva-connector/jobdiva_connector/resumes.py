"""Select the latest JobDiva resume only when its timestamp is unambiguous."""
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .client import JobDivaError


def latest_resume_id(
    records: list[dict[str, Any]],
    *,
    date_format: str | None = None,
    source_timezone: str | None = None,
) -> str | None:
    if not records:
        return None

    dated: list[tuple[datetime, str]] = []
    for record in records:
        resume_id = record.get("RESUMEID", record.get("resumeId", record.get("id")))
        if isinstance(resume_id, bool) or not isinstance(resume_id, (str, int)):
            raise JobDivaError("Resume ID is missing; select the version manually")
        resume_id = str(resume_id).strip()
        if not resume_id or not resume_id.isascii() or not resume_id.isdigit():
            raise JobDivaError("Resume ID is invalid; select the version manually")

        value = record.get("DATECREATED", record.get("resumeDate", record.get("createdAt")))
        if not isinstance(value, str) or not value.strip():
            raise JobDivaError("Resume creation date is missing; select the version manually")
        value = value.strip()
        try:
            created = datetime.strptime(value, date_format) if date_format else datetime.fromisoformat(value.replace("Z", "+00:00"))
            if created.tzinfo is None:
                if not source_timezone:
                    raise JobDivaError("Confirm the JobDiva time zone before comparing naive resume dates")
                zone = ZoneInfo(source_timezone)
                first = created.replace(tzinfo=zone, fold=0)
                second = created.replace(tzinfo=zone, fold=1)
                if first.utcoffset() != second.utcoffset():
                    raise JobDivaError("Resume time is ambiguous around a daylight-saving transition")
                created = first
        except JobDivaError:
            raise
        except ZoneInfoNotFoundError:
            raise JobDivaError("The configured JobDiva time zone is unknown") from None
        except (ValueError, TypeError):
            raise JobDivaError("Resume date does not match the reviewed date format") from None
        dated.append((created, str(int(resume_id))))

    newest = max(date for date, _ in dated)
    choices = {resume_id for date, resume_id in dated if date == newest}
    if len(choices) != 1:
        raise JobDivaError("Multiple resumes share the latest timestamp; select the version manually")
    return choices.pop()
