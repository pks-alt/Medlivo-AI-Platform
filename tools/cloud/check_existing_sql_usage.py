import json
import math
import os
import subprocess
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener

PROJECT = "medlivo-ai-platform"
INSTANCE = "medlivo-ai-postgres"
END = datetime.now(timezone.utc) - timedelta(minutes=5)
START = END - timedelta(days=7)

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = build_opener(NoRedirect())

def cloud(arguments):
    result = subprocess.run(
        ["gcloud", *arguments, "--project=" + PROJECT, "--quiet", "--no-log-http"],
        capture_output=True, text=True, timeout=45,
        env={**os.environ, "CLOUDSDK_CORE_LOG_HTTP": "false"},
    )
    if result.returncode:
        raise RuntimeError("Google Cloud read failed; no settings were changed.")
    return result.stdout.strip()

try:
    token = cloud(["auth", "print-access-token"])
except (RuntimeError, OSError, subprocess.TimeoutExpired):
    raise SystemExit("STOP: Could not obtain your existing Google Cloud authentication.")

print("=== Existing SQL server usage: available samples from the last 7 days ===")
print("Requested UTC interval:", START.isoformat(), "to", END.isoformat())
metrics = [
    ("CPU used", "cpu/utilization", 100, "%"),
    ("Memory used", "memory/utilization", 100, "%"),
    ("Disk used", "disk/utilization", 100, "%"),
    ("Disk data", "disk/bytes_used", 1 / (1024 ** 3), "GiB"),
]
for label, metric, scale, unit in metrics:
    parameters = {
        "filter": 'metric.type="cloudsql.googleapis.com/database/' + metric + '" '
                  'AND resource.type="cloudsql_database" '
                  'AND resource.labels.database_id="' + PROJECT + ':' + INSTANCE + '"',
        "interval.startTime": START.isoformat(),
        "interval.endTime": END.isoformat(),
        "view": "FULL", "pageSize": 20000,
    }
    request = Request(
        "https://monitoring.googleapis.com/v3/projects/" + PROJECT + "/timeSeries?" + urlencode(parameters),
        headers={"Authorization": "Bearer " + token},
    )
    try:
        with opener.open(request, timeout=30) as response:
            data = json.load(response)
        series = data.get("timeSeries", [])
        if data.get("nextPageToken") or data.get("executionErrors") or len(series) != 1:
            print(label + ": UNKNOWN (missing, incomplete, or multiple metric series)")
            continue
        points = series[0].get("points", [])
        readings = []
        for point in points:
            value = point["value"]
            number = float(value["doubleValue"] if "doubleValue" in value else value["int64Value"]) * scale
            if not math.isfinite(number):
                raise ValueError()
            readings.append((point["interval"]["endTime"], number))
        readings.sort()
        if not readings:
            print(label + ": UNKNOWN (no samples)")
            continue
        numbers = [reading[1] for reading in readings]
        print(f"{label}: sample average {sum(numbers)/len(numbers):.1f}{unit}; "
              f"sample peak {max(numbers):.1f}{unit}; latest {readings[-1][1]:.1f}{unit}")
        print(f"  {len(readings)} samples, {readings[0][0]} to {readings[-1][0]}")
    except HTTPError as error:
        print(f"{label}: UNKNOWN (Monitoring HTTP {error.code})")
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
        print(label + ": UNKNOWN (metric could not be read)")

del token
print("\n=== Cloud Run services declaring this SQL connection in us-west1 ===")
try:
    services = json.loads(cloud(["run", "services", "list", "--region=us-west1", "--format=json"]))
    found = False
    for service in services:
        template = service.get("spec", {}).get("template", {})
        annotations = template.get("metadata", {}).get("annotations", {})
        instances = annotations.get("run.googleapis.com/cloudsql-instances", "").split(",")
        if not any(item.strip().endswith(":" + INSTANCE) for item in instances):
            continue
        found = True
        modes = []
        for container in template.get("spec", {}).get("containers", []):
            for setting in container.get("env", []):
                if setting.get("name") == "USE_MOCK_DATA":
                    modes.append(setting.get("value") if setting.get("value") in ("true", "false") else "unknown")
        print(service.get("metadata", {}).get("name", "unnamed"), "| USE_MOCK_DATA:", ", ".join(modes) or "not declared")
    if not found:
        print("No matching connection annotation found. This does NOT prove the server is unused.")
except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError, TypeError, AttributeError):
    print("UNKNOWN: Could not read Cloud Run connection metadata.")
print("Other clients and older revisions are not covered by this service listing.")
print("\nRead-only checks completed. No database, permissions, or service settings changed.")
