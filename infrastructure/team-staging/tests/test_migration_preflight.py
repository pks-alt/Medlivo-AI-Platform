import contextlib
import importlib.util
import io
import json
import re
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "migration_preflight", ROOT / "infrastructure/team-staging/migration_preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


def good_values():
    return {
        "service_account": {"ok": True, "value": {"email": preflight.SERVICE_ACCOUNT, "disabled": False}},
        "secret": {"ok": True, "value": {"name": f"projects/{preflight.PROJECT}/secrets/{preflight.SECRET}"}},
        "service_account_inventory": {"ok": True, "value": [{"email": preflight.SERVICE_ACCOUNT}]},
        "secret_inventory": {"ok": True, "value": [{"name": f"projects/{preflight.PROJECT}/secrets/{preflight.SECRET}"}]},
    }


class MigrationPreflightTests(unittest.TestCase):
    def test_success_is_metadata_only_not_deployed(self):
        result = preflight.inspect(reader=good_values().__getitem__, include_inventory=True)
        self.assertTrue(result["preflight_passed"])
        self.assertFalse(result["cloud_modified"])
        self.assertFalse(result["database_checked"])
        self.assertFalse(result["secret_values_read"])
        self.assertFalse(result["serving_release_verified"])
        self.assertEqual(result["schema_ready"], "not_checked")

    def test_both_lookups_run_when_first_is_denied(self):
        data = good_values()
        data["service_account"] = {"ok": False, "status": "permission_denied_or_not_visible"}
        called = []
        def reader(key):
            called.append(key)
            return data[key]
        result = preflight.inspect(reader=reader)
        self.assertEqual(called, ["service_account", "secret"])
        self.assertFalse(result["preflight_passed"])
        self.assertEqual(result["checks"][0]["presence"], "unknown")
        self.assertNotIn("missing", result["checks"][0]["status"])

    def test_inventory_can_prove_presence_but_not_bypass_failed_lookup(self):
        data = good_values()
        data["service_account"] = {"ok": False, "status": "permission_denied_or_not_visible"}
        result = preflight.inspect(reader=data.__getitem__, include_inventory=True)
        self.assertEqual(result["checks"][0]["presence"], "confirmed_by_inventory")
        self.assertFalse(result["preflight_passed"])

    def test_empty_inventory_does_not_become_verified_or_instruction_to_create(self):
        data = good_values()
        data["service_account"] = {"ok": False, "status": "not_found_response"}
        data["service_account_inventory"]["value"] = []
        result = preflight.inspect(reader=data.__getitem__, include_inventory=True)
        self.assertFalse(result["inventory"][0]["target_listed"])
        self.assertEqual(result["checks"][0]["presence"], "unknown")
        self.assertFalse(result["preflight_passed"])

    def test_inventory_permission_failure_is_not_an_empty_inventory(self):
        data = good_values()
        data["service_account_inventory"] = {"ok": False, "status": "permission_denied_or_not_visible"}
        result = preflight.inspect(reader=data.__getitem__, include_inventory=True)
        self.assertIsNone(result["inventory"][0]["target_listed"])
        self.assertEqual(result["inventory"][0]["status"], "permission_denied_or_not_visible")

    def test_disabled_account_cannot_pass(self):
        data = good_values()
        data["service_account"]["value"]["disabled"] = True
        result = preflight.inspect(reader=data.__getitem__)
        self.assertFalse(result["preflight_passed"])
        self.assertEqual(result["checks"][0]["status"], "disabled")

    def test_wrong_resource_or_malformed_describe_cannot_pass(self):
        for value in (None, [], {}, {"email": "other@example.com"},
                      {"email": preflight.SERVICE_ACCOUNT, "disabled": "false"}):
            with self.subTest(value=value):
                data = good_values()
                data["service_account"]["value"] = value
                self.assertFalse(preflight.inspect(reader=data.__getitem__)["preflight_passed"])

    def test_secret_numeric_project_reference_is_supported(self):
        data = good_values()
        data["secret"]["value"]["name"] = f"projects/363168336964/secrets/{preflight.SECRET}"
        self.assertTrue(preflight.inspect(reader=data.__getitem__)["preflight_passed"])

    def test_unrelated_secret_reference_is_rejected(self):
        data = good_values()
        data["secret"]["value"]["name"] = f"projects/unapproved-project/secrets/{preflight.SECRET}"
        self.assertFalse(preflight.inspect(reader=data.__getitem__)["preflight_passed"])

    def test_default_compute_account_does_not_invalidate_inventory(self):
        data = good_values()
        data["service_account_inventory"]["value"].append({"email": "363168336964-compute@developer.gserviceaccount.com"})
        result = preflight.inspect(reader=data.__getitem__, include_inventory=True)
        self.assertEqual(result["inventory"][0]["status"], "metadata_listed")
        self.assertTrue(result["inventory"][0]["target_listed"])

    def test_alternative_resource_is_listed_but_not_adopted(self):
        data = good_values()
        data["service_account"] = {"ok": False, "status": "lookup_failed"}
        alternative = f"medlivo-existing-migrator@{preflight.PROJECT}.iam.gserviceaccount.com"
        data["service_account_inventory"]["value"] = [{"email": alternative}]
        result = preflight.inspect(reader=data.__getitem__, include_inventory=True)
        self.assertIn(alternative, result["inventory"][0]["candidates"])
        self.assertEqual(result["checks"][0]["resource"], preflight.SERVICE_ACCOUNT)
        self.assertFalse(result["preflight_passed"])

    def test_invalid_inventory_does_not_claim_target_absent(self):
        data = good_values()
        data["service_account_inventory"]["value"] = [{"unexpected": "data"}]
        result = preflight.inspect(reader=data.__getitem__, include_inventory=True)
        self.assertIsNone(result["inventory"][0]["target_listed"])
        self.assertEqual(result["inventory"][0]["status"], "invalid_metadata_response")

    def test_failed_command_error_classes_and_no_raw_errors(self):
        cases = {
            "PERMISSION_DENIED: resource does not exist or permission denied": "permission_denied_or_not_visible",
            "NOT_FOUND: example": "not_found_response",
            "UNAUTHENTICATED: invalid token": "authentication_failed",
            "connection timed out": "transient_or_network_error",
            "unknown failure": "lookup_failed",
        }
        for error, status in cases.items():
            with self.subTest(error=error):
                runner = lambda *args, **kw: subprocess.CompletedProcess([], 1, "sensitive-payload", error + " fake-secret-marker")
                result = preflight.read_metadata("service_account", runner=runner)
                self.assertEqual(result["status"], status)
                self.assertNotIn("fake-secret-marker", json.dumps(result))
                self.assertNotIn("sensitive-payload", json.dumps(result))

    def test_timeout_and_missing_gcloud_fail_closed(self):
        for error, status in ((subprocess.TimeoutExpired("gcloud", 45), "lookup_timeout"),
                              (FileNotFoundError(), "gcloud_unavailable"),
                              (OSError(), "command_unavailable")):
            with self.subTest(status=status):
                def runner(*args, **kw):
                    raise error
                self.assertEqual(preflight.read_metadata("secret", runner=runner)["status"], status)

    def test_invalid_json_is_not_success(self):
        runner = lambda *args, **kw: subprocess.CompletedProcess([], 0, "not json", "")
        self.assertFalse(preflight.read_metadata("secret", runner=runner)["ok"])

    def test_only_fixed_metadata_commands_are_invoked(self):
        commands = []
        def runner(command, **kw):
            commands.append(command)
            self.assertEqual(kw["timeout"], 45)
            self.assertTrue(kw["capture_output"])
            self.assertNotIn("shell", kw)
            return subprocess.CompletedProcess(command, 0, "{}", "")
        for key in preflight.COMMANDS:
            preflight.read_metadata(key, runner=runner)
        for command in commands:
            self.assertIn(f"--project={preflight.PROJECT}", command)
            self.assertIn("--no-log-http", command)
            self.assertTrue("describe" in command or "list" in command)
            self.assertFalse(set(command) & {"access", "deploy", "create", "update", "delete", "execute", "set-iam-policy"})
        with self.assertRaises(ValueError):
            preflight.read_metadata("secret_values", runner=runner)

    def test_cli_failure_exits_nonzero_without_touching_cloud(self):
        with patch.object(preflight, "inspect", return_value={"preflight_passed": False}), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(preflight.main(["--inventory"]), 1)
        self.assertFalse(json.loads(output.getvalue())["preflight_passed"])

    def test_report_drops_unexpected_metadata_and_secret_fields(self):
        data = good_values()
        data["secret"]["value"]["payload"] = "fake-secret-marker"
        data["service_account_inventory"]["value"][0]["token"] = "fake-token-marker"
        text = json.dumps(preflight.inspect(reader=data.__getitem__, include_inventory=True))
        self.assertNotIn("fake-secret-marker", text)
        self.assertNotIn("fake-token-marker", text)


class WorkflowPreflightTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (ROOT / ".github/workflows/deploy-team-staging.yml").read_text()
        self.guard = "if: ${{ github.event_name != 'workflow_dispatch' || !inputs.diagnostics_only }}"

    def test_preflight_precedes_build_and_migration(self):
        before = self.workflow.index("Verify staging migration identity")
        self.assertLess(before, self.workflow.index("Configure Artifact Registry"))
        self.assertLess(before, self.workflow.index("Build and push private API"))
        self.assertLess(before, self.workflow.index("Apply reviewed workspace migrations 014-021"))
        for migration in (
            "014_job_content_standards.sql",
            "015_recruiter_execution_controls.sql",
            "016_outreach_drafts.sql",
            "017_outreach_execution.sql",
            "018_gmail_provider_pilot.sql",
            "019_gmail_reply_sync.sql",
            "020_followup_sequences.sql",
            "021_scheduled_followup_execution.sql",
        ):
            self.assertIn(migration, self.workflow)

    def test_diagnostic_mode_is_explicit_and_default_for_manual_runs(self):
        inputs = self.workflow.split("workflow_dispatch:", 1)[1].split("permissions:", 1)[0]
        self.assertIn("diagnostics_only:", inputs)
        self.assertIn("type: boolean", inputs)
        self.assertIn("default: true", inputs)
        self.assertIn("required: true", inputs)

    def test_all_cloud_mutating_steps_skip_in_diagnostic_mode(self):
        steps = re.split(r"(?m)(?=      - (?:name:|uses:|id:))", self.workflow)
        count = 0
        for step in steps:
            if any(token in step for token in ("docker build", "docker push", "gcloud auth configure-docker", "gcloud run jobs", "gcloud run deploy", "gcloud run services update")):
                self.assertIn(self.guard, step)
                count += 1
        self.assertEqual(count, 8)

    def test_readonly_step_cannot_be_skipped_by_diagnostic_flag(self):
        step = self.workflow.split("- name: Verify staging migration identity", 1)[1].split("- name:", 1)[0]
        self.assertNotIn("if:", step)
        self.assertIn("migration_preflight.py --inventory", step)
        self.assertNotIn("continue-on-error", step)

    def test_previous_misleading_error_is_removed(self):
        self.assertNotIn("Missing dedicated staging migration service account", self.workflow)
        self.assertNotIn("Missing staging migration database secret", self.workflow)
        self.assertNotIn("/dev/null 2>&1", self.workflow)

    def test_release_security_gates_and_existing_identity_remain(self):
        self.assertIn("httpGet.path=/ready", self.workflow)
        self.assertIn("--no-traffic", self.workflow)
        self.assertIn("medlivo-team-staging-migration-database-url:latest", self.workflow)
        self.assertNotIn("WORKSPACE_DATABASE_URL=medlivo-team-staging-api-database-url", self.workflow)
        self.assertIn("Verify deployed release SHA", self.workflow)
        self.assertNotIn("pull_request_target", self.workflow)

    def test_offline_diagnostic_tests_run_in_unfiltered_control_workflow(self):
        control = (ROOT / ".github/workflows/platform-control.yml").read_text()
        self.assertIn("pull_request:", control)
        self.assertNotIn("paths:", control)
        self.assertIn("test_migration_preflight.py", control)
        self.assertNotIn("id-token:", control)


if __name__ == "__main__":
    unittest.main()
