"""Read-only migration-resource diagnostics for the existing staging release.

No secret values, database access, resource creation, IAM changes or deployment.
A denied describe call does NOT establish that a service account is missing:
https://docs.cloud.google.com/sdk/gcloud/reference/iam/service-accounts/describe
Only fixed metadata commands are accepted. Raw output/errors are never emitted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import subprocess
from typing import Callable

PROJECT = "medlivo-ai-platform"
SERVICE_ACCOUNT = f"medlivo-team-schema-staging@{PROJECT}.iam.gserviceaccount.com"
SECRET = "medlivo-team-staging-migration-database-url"
COMMANDS = {
    "service_account": ["iam", "service-accounts", "describe", SERVICE_ACCOUNT,
                        "--format=json(email,disabled)"],
    "secret": ["secrets", "describe", SECRET, "--format=json(name)"],
    "service_account_inventory": ["iam", "service-accounts", "list",
                                  "--format=json(email,disabled)"],
    "secret_inventory": ["secrets", "list", "--format=json(name)"],
}


def _error_class(error: str) -> str:
    # Preserve uncertainty: Google can return PERMISSION_DENIED for absent SAs.
    upper = error.upper()
    if any(x in upper for x in ("PERMISSION_DENIED", "PERMISSION DENIED", "FORBIDDEN", "HTTP 403")):
        return "permission_denied_or_not_visible"
    if any(x in upper for x in ("UNAUTHENTICATED", "INVALID_GRANT", "REAUTH", "NO ACTIVE ACCOUNT")):
        return "authentication_failed"
    if "NOT_FOUND" in upper or "HTTP 404" in upper:
        return "not_found_response"
    if any(x in upper for x in ("DEADLINE_EXCEEDED", "UNAVAILABLE", "CONNECTION", "TIMED OUT", "TIMEOUT")):
        return "transient_or_network_error"
    return "lookup_failed"


def read_metadata(key: str, *, runner: Callable = subprocess.run) -> dict:
    """Return only parsed metadata or a fixed error class, never raw diagnostics."""
    if key not in COMMANDS:
        raise ValueError("Unapproved metadata operation")
    command = ["gcloud", *COMMANDS[key], f"--project={PROJECT}",
               "--quiet", "--no-log-http", "--verbosity=error"]
    try:
        result = runner(command, capture_output=True, text=True, timeout=45, check=False)
    except FileNotFoundError:
        return {"ok": False, "status": "gcloud_unavailable"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "status": "lookup_timeout"}
    except OSError:
        return {"ok": False, "status": "command_unavailable"}
    if result.returncode:
        return {"ok": False, "status": _error_class(result.stderr or "")}
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        return {"ok": False, "status": "invalid_metadata_response"}
    return {"ok": True, "value": value}


def _check(kind: str, result: dict) -> dict:
    check = {"kind": kind, "resource": SERVICE_ACCOUNT if kind == "service_account" else SECRET,
             "status": result.get("status", "invalid_metadata_response"), "presence": "unknown"}
    if not result.get("ok"):
        # Even NOT_FOUND remains a reported lookup result, not a create instruction.
        return check
    value = result.get("value")
    if not isinstance(value, dict):
        check["status"] = "invalid_metadata_response"
        return check
    if kind == "service_account":
        valid = value.get("email") == SERVICE_ACCOUNT and isinstance(value.get("disabled", False), bool)
        disabled = value.get("disabled", False)
    else:
        name = value.get("name", "")
        valid = isinstance(name, str) and bool(re.fullmatch(
            rf"projects/(?:{re.escape(PROJECT)}|[0-9]+)/secrets/{re.escape(SECRET)}", name))
        disabled = False
    if not valid:
        check["status"] = "invalid_metadata_response"
        return check
    check.update(presence="confirmed", status="disabled" if disabled else "metadata_verified")
    return check


def _inventory(kind: str, result: dict, check: dict) -> dict:
    """Show only relevant resource names; never adopt an alternative automatically."""
    report = {"kind": kind, "status": result.get("status", "invalid_metadata_response"),
              "target_listed": None, "candidates": []}
    values = result.get("value")
    if not result.get("ok") or not isinstance(values, list):
        return report
    names = []
    for row in values:
        if not isinstance(row, dict):
            report["status"] = "invalid_metadata_response"
            return report
        if kind == "service_account":
            name = row.get("email")
            valid = isinstance(name, str) and bool(re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._+-]*@[A-Za-z0-9.-]+\.gserviceaccount\.com", name))
        else:
            full_name = row.get("name")
            valid = isinstance(full_name, str) and bool(re.fullmatch(
                rf"projects/(?:{re.escape(PROJECT)}|[0-9]+)/secrets/[A-Za-z0-9_-]+", full_name))
            name = full_name.rsplit("/", 1)[-1] if valid else None
        if not valid:
            # A malformed/incomplete listing must not be reported as an empty one.
            report["status"] = "invalid_metadata_response"
            return report
        names.append(name)
    target = SERVICE_ACCOUNT if kind == "service_account" else SECRET
    report.update(status="metadata_listed", target_listed=target in names,
                  candidates=sorted({name for name in names
                                     if any(word in name.lower() for word in ("medlivo", "migration", "schema"))}))
    check["inventory_evidence"] = "target_listed" if target in names else "target_not_listed"
    if target in names:
        check["presence"] = "confirmed_by_inventory"
    # The deploy gate still requires successful direct lookup, not just a list.
    return report


def inspect(*, reader: Callable = read_metadata, include_inventory: bool = False) -> dict:
    checks = [_check(kind, reader(kind)) for kind in ("service_account", "secret")]
    inventories = []
    if include_inventory:
        for check in checks:
            kind = check["kind"]
            inventories.append(_inventory(kind, reader(kind + "_inventory"), check))
    passed = all(check["status"] == "metadata_verified" for check in checks)
    return {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "project": PROJECT,
        "mode": "read_only_metadata",
        "preflight_passed": passed,
        "cloud_modified": False,
        "secret_values_read": False,
        "database_checked": False,
        "schema_ready": "not_checked",
        "serving_release_verified": False,
        "checks": checks,
        "inventory": inventories,
        "next_action": (
            "Metadata prerequisite passed only. Migration privileges, schema and serving release still require verification."
            if passed else
            "Stop deployment. Review lookup classes and visible inventory; do not create, replace, or grant access automatically."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_true", help="Also list resource names in the same fixed project")
    args = parser.parse_args(argv)
    report = inspect(include_inventory=args.inventory)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["preflight_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
