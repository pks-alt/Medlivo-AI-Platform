"""Staging-only manifests and metadata inventory. No deployment or secret reads.

Python 3.12+, standard library only. The Cloud inventory executes a fixed set of
read-only gcloud commands; it never accesses secret values or returns raw errors.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

PROJECT = "medlivo-ai-platform"
REGION = "us-west1"
API = "medlivo-team-api-staging"
WEB = "medlivo-team-web-staging"
SQL = "medlivo-team-staging"
REGISTRY = f"{REGION}-docker.pkg.dev/{PROJECT}/medlivo-ai-containers"
SECRETS = {
    "WORKSPACE_DATABASE_URL": "medlivo-team-staging-api-database-url",
    "TEAM_SESSION_DATABASE_URL": "medlivo-team-staging-session-database-url",
    "TEAM_GOOGLE_CLIENT_SECRET": "medlivo-team-staging-google-client-secret",
    "TEAM_SESSION_KEY": "medlivo-team-staging-session-key",
}
REQUIRED_APIS = {"run.googleapis.com", "sqladmin.googleapis.com", "secretmanager.googleapis.com", "artifactregistry.googleapis.com"}


class ConfigurationError(ValueError):
    pass


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ConfigurationError("Unexpected or missing configuration fields; do not include credentials")


def origin(value, service):
    if not isinstance(value, str):
        raise ConfigurationError("Copy the staging service status.url after private bootstrap")
    parsed = urlsplit(value)
    # Limit the first pilot to the two named run.app services; no custom domains.
    if (parsed.scheme != "https" or parsed.netloc != parsed.hostname or parsed.path or parsed.query or parsed.fragment
            or not re.fullmatch(re.escape(service) + r"-[a-z0-9][a-z0-9.-]*\.run\.app", parsed.hostname or "")):
        raise ConfigurationError("Use the exact HTTPS root URL of the designated staging service")
    return value


def validate(config, mode):
    base = {"project", "region", "environment", "images"}
    expected = base if mode == "bootstrap" else base | {"app_origin", "api_url", "google_client_id", "secret_versions", "reviewed"}
    exact_keys(config, expected)
    if (config["project"], config["region"], config["environment"]) != (PROJECT, REGION, "staging"):
        raise ConfigurationError("This tool only prepares the named Medlivo staging environment")
    exact_keys(config["images"], {"api", "web"})
    for key, service in (("api", API), ("web", WEB)):
        image = config["images"][key]
        if not isinstance(image, str) or not re.fullmatch(re.escape(f"{REGISTRY}/{service}@sha256:") + r"[0-9a-f]{64}", image):
            raise ConfigurationError("Use a built staging image pinned by its sha256 digest; mutable tags are not accepted")
    if mode == "configured":
        origin(config["app_origin"], WEB)
        origin(config["api_url"], API)
        if not isinstance(config["google_client_id"], str) or not re.fullmatch(r"[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com", config["google_client_id"]):
            raise ConfigurationError("Use the approved Google OAuth web client ID, not its secret")
        exact_keys(config["secret_versions"], set(SECRETS))
        for version in config["secret_versions"].values():
            if not isinstance(version, str) or not re.fullmatch(r"[1-9][0-9]*", version):
                raise ConfigurationError("Secret references must use specific numeric versions, not latest or raw values")
        required = {"staging_database_and_grants", "oauth_callback_registered", "synthetic_users_only", "callback_logs_redacted"}
        exact_keys(config["reviewed"], required)
        if any(value is not True for value in config["reviewed"].values()):
            raise ConfigurationError("Complete the operator reviews before preparing an enabled configuration")
    return config


def manifest(service, image, env, configured):
    annotations = {"run.googleapis.com/execution-environment": "gen2", "autoscaling.knative.dev/maxScale": "2"}
    if configured:
        annotations["run.googleapis.com/cloudsql-instances"] = f"{PROJECT}:{REGION}:{SQL}"
    return {
        "apiVersion": "serving.knative.dev/v1", "kind": "Service",
        "metadata": {"name": service, "labels": {"environment": "staging", "app": "medlivo-team"},
                     "annotations": {"run.googleapis.com/ingress": "all", "run.googleapis.com/invoker-iam-disabled": "false"}},
        "spec": {"template": {"metadata": {"annotations": annotations}, "spec": {
            "serviceAccountName": f"{service}@{PROJECT}.iam.gserviceaccount.com",
            "containerConcurrency": 10, "timeoutSeconds": 60,
            "containers": [{"image": image, "ports": [{"containerPort": 8080}],
                            "resources": {"limits": {"cpu": "1", "memory": "512Mi"}}, "env": env}],
        }}, "traffic": [{"latestRevision": True, "percent": 100}]},
    }


def render(config, mode):
    c = validate(config, mode)
    configured = mode == "configured"
    enabled = "true" if configured else "false"
    api_env = [{"name": "WORKSPACE_ENABLED", "value": enabled}]
    web_env = [{"name": "TEAM_WORKSPACE_ENABLED", "value": enabled}, {"name": "NEXT_TELEMETRY_DISABLED", "value": "1"}]
    if configured:
        api_env += [{"name": "WORKSPACE_GOOGLE_CLIENT_ID", "value": c["google_client_id"]},
                    {"name": "WORKSPACE_GOOGLE_HOSTED_DOMAIN", "value": "medlivo.com"}]
        web_env += [{"name": key, "value": val} for key, val in {
            "TEAM_APP_ORIGIN": c["app_origin"], "TEAM_API_URL": c["api_url"],
            "TEAM_GOOGLE_CLIENT_ID": c["google_client_id"], "TEAM_GOOGLE_HOSTED_DOMAIN": "medlivo.com"}.items()]
        for variable, secret in SECRETS.items():
            target = api_env if variable == "WORKSPACE_DATABASE_URL" else web_env
            target.append({"name": variable, "valueFrom": {"secretKeyRef": {"name": secret, "key": c["secret_versions"][variable]}}})
    return {"api": manifest(API, c["images"]["api"], api_env, configured),
            "web": manifest(WEB, c["images"]["web"], web_env, configured)}


def cloud_json(arguments):
    """Only called with fixed read operations below. No shell or returned stderr."""
    try:
        result = subprocess.run(["gcloud", *arguments, f"--project={PROJECT}", "--format=json", "--quiet"],
                                capture_output=True, text=True, timeout=45, check=False)
        if result.returncode:
            return {"readable": False, "reason": "Metadata read failed or permission was denied"}
        return {"readable": True, "value": json.loads(result.stdout)}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"readable": False, "reason": "gcloud unavailable, timed out, or returned invalid JSON"}


def inventory(reader=cloud_json):
    report = {"project": PROJECT, "region": REGION, "mode": "read_only_metadata",
              "generated_at": datetime.now(timezone.utc).isoformat(), "cloud_modified": False,
              "secret_values_read": False, "ready_to_enable": False, "checks": []}
    def add(name, status, detail):
        report["checks"].append({"name": name, "status": status, "detail": detail})
    enabled = reader(["services", "list", "--enabled"])
    if not enabled["readable"]:
        add("required_apis", "unknown", enabled["reason"])
    else:
        present = {r.get("config", {}).get("name") for r in enabled["value"]}
        missing = sorted(REQUIRED_APIS - present)
        add("required_apis", "missing" if missing else "pass", {"missing": missing})
    services = reader(["run", "services", "list", f"--region={REGION}"])
    if not services["readable"]:
        add("staging_services", "unknown", services["reason"])
    else:
        by_name = {item.get("metadata", {}).get("name"): item for item in services["value"]}
        for service in (API, WEB):
            item = by_name.get(service)
            if item is None:
                add(service, "missing", "Designated staging service is not listed; do not reuse a production service")
                continue
            metadata = item.get("metadata", {})
            anns = metadata.get("annotations", {})
            runtime = item.get("spec", {}).get("template", {}).get("spec", {})
            disabled = anns.get("run.googleapis.com/invoker-iam-disabled", "false")
            env = {e.get("name"): e for e in runtime.get("containers", [{}])[0].get("env", [])}
            flag = "WORKSPACE_ENABLED" if service == API else "TEAM_WORKSPACE_ENABLED"
            detail = {"url": item.get("status", {}).get("url"),
                      "staging_label": metadata.get("labels", {}).get("environment") == "staging",
                      "dedicated_identity": runtime.get("serviceAccountName") == f"{service}@{PROJECT}.iam.gserviceaccount.com",
                      "invoker_check_enabled": disabled != "true", "application_enabled": env.get(flag, {}).get("value") == "true"}
            safe = detail["staging_label"] and detail["dedicated_identity"] and detail["invoker_check_enabled"]
            add(service, "pass" if safe else "review", detail)
            policy = reader(["run", "services", "get-iam-policy", service, f"--region={REGION}"])
            if not policy["readable"]:
                add(service + "_iam", "unknown", policy["reason"])
            else:
                public = any(member in {"allUsers", "allAuthenticatedUsers"}
                             for b in policy["value"].get("bindings", []) for member in b.get("members", []))
                invoker = any(b.get("role") == "roles/run.invoker" and not b.get("condition") and
                              f"serviceAccount:{WEB}@{PROJECT}.iam.gserviceaccount.com" in b.get("members", [])
                              for b in policy["value"].get("bindings", []))
                add(service + "_iam", "review" if public else "pass",
                    {"public_binding_present": public, "web_to_api_direct_invoker_binding": invoker if service == API else None,
                     "note": "Service-level bindings only; inherited/conditional permissions still require operator review"})
    accounts = reader(["iam", "service-accounts", "list"])
    if not accounts["readable"]:
        add("staging_service_accounts", "unknown", accounts["reason"])
    else:
        present = {r.get("email") for r in accounts["value"] if not r.get("disabled")}
        missing = [s for s in (API, WEB) if f"{s}@{PROJECT}.iam.gserviceaccount.com" not in present]
        add("staging_service_accounts", "missing" if missing else "pass", {"missing": missing})
    sql = reader(["sql", "instances", "list"])
    if not sql["readable"]:
        add("staging_database", "unknown", sql["reason"])
    else:
        found = next((s for s in sql["value"] if s.get("name") == SQL), None)
        if not found:
            add("staging_database", "missing", "Dedicated staging SQL instance not listed; no database was created or reused")
        else:
            ok = found.get("region") == REGION and found.get("state") == "RUNNABLE" and str(found.get("databaseVersion", "")).startswith("POSTGRES_")
            add("staging_database", "pass" if ok else "review",
                {"name": SQL, "region_matches": found.get("region") == REGION, "runnable_postgres": ok,
                 "note": "Does not verify schema, grants, secrets, backups or application connectivity"})
    secrets = reader(["secrets", "list"])
    if not secrets["readable"]:
        add("staging_secret_metadata", "unknown", secrets["reason"])
    else:
        names = {r.get("name", "").rsplit("/", 1)[-1] for r in secrets["value"]}
        missing = [name for name in SECRETS.values() if name not in names]
        add("staging_secret_metadata", "missing" if missing else "pass",
            {"missing": missing, "note": "Existence only; values, versions and runtime access have not been checked"})
    add("oauth_and_member_provisioning", "manual", "Confirm OAuth web client/callback, approved Google subjects, and synthetic cases with an administrator")
    add("live_acceptance", "not_run", "Real Google sign-in, database permissions, metadata tokens and two-user workflow remain unverified")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="Fixed read-only gcloud metadata checks; never reads secret values")
    inv.add_argument("--output", type=Path)
    out = sub.add_parser("render", help="Write private service specifications locally; DOES NOT deploy")
    out.add_argument("--mode", choices=("bootstrap", "configured"), default="bootstrap")
    out.add_argument("--config", type=Path, required=True)
    out.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.command == "inventory":
            report = inventory()
            text = json.dumps(report, indent=2)
            if args.output:
                args.output.write_text(text + "\n")
            print(text)
            # Metadata gaps should not be presented as a failed deployment.
            return 0
        config = json.loads(args.config.read_text())
        specs = render(config, args.mode)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for kind, spec in specs.items():
            # JSON is valid YAML for Cloud Run's Knative service specification.
            path = args.output_dir / f"{kind}.service.json"
            with path.open("x", encoding="utf-8") as target:
                target.write(json.dumps(spec, indent=2) + "\n")
        print("Prepared two PRIVATE staging specifications. No deployment, IAM changes or secret reads performed.")
        print("Operator review is required before gcloud run services replace --dry-run and any subsequent deployment.")
        return 0
    except (ConfigurationError, OSError, ValueError):
        print("Configuration/output could not be validated. Check required fields and use a new output directory; do not share secrets.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
