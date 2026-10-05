"""Select the latest resume only when its date is unambiguous."""
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .contracts import ContractError
from .client import _ids


def latest_resume_id(records: list[dict[str, Any]], *, date_format: str | None = None,
                     source_timezone: str | None = None) -> str | None:
    if not records:
        return None
    dated: list[tuple[datetime, str]] = []
    for record in records:
        value = record.get("DATECREATED")
        if not isinstance(value, str):
            raise ContractError("Resume creation date is missing; select the version manually")
        try:
            created = datetime.strptime(value, date_format) if date_format else datetime.fromisoformat(value)
            if created.tzinfo is None:
                if not source_timezone:
                    raise ContractError("Confirm the JobDiva time zone before comparing naive dates")
                zone = ZoneInfo(source_timezone)
                first, second = created.replace(tzinfo=zone, fold=0), created.replace(tzinfo=zone, fold=1)
                if first.utcoffset() != second.utcoffset():
                    raise ContractError("Resume time is ambiguous around a daylight-saving transition")
                created = first
        except ContractError:
            raise
        except ZoneInfoNotFoundError:
            raise ContractError("The configured JobDiva time zone is unknown") from None
        except (ValueError, TypeError):
            raise ContractError("Resume date does not match the reviewed date format") from None
        ident = _ids([record.get("RESUMEID")])[0]
        dated.append((created, ident))
    newest = max(date for date, _ in dated)
    choices = {ident for date, ident in dated if date == newest}
    if len(choices) != 1:
        raise ContractError("Multiple resumes share the latest timestamp; select the version manually")
    return choices.pop()
