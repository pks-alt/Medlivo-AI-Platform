import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]


class FollowupWorkerTests(unittest.TestCase):
    def test_worker_creates_review_only_drafts(self):
        worker = (ROOT / "services/team-workspace/workspace_api/followup_worker.py").read_text()
        self.assertIn("prepare_due_followups_system", worker)
        self.assertIn('"automatic_send_enabled": False', worker)
        self.assertNotIn("deliver_gmail_execution", worker)
        self.assertNotIn("send_message(", worker)

    def test_staging_scheduler_runs_every_fifteen_minutes(self):
        workflow = (ROOT / ".github/workflows/followup-due-staging.yml").read_text()
        self.assertIn('cron: "*/15 * * * *"', workflow)
        self.assertIn("medlivo-followup-due-staging", workflow)
        self.assertIn("gcloud run jobs execute", workflow)

    def test_deploy_reuses_private_api_identity_and_secret_metadata(self):
        workflow = (ROOT / ".github/workflows/deploy-team-staging.yml").read_text()
        self.assertIn("Deploy automatic due follow-up preparation job", workflow)
        self.assertIn('API_DB_SECRET="$(gcloud run services describe', workflow)
        self.assertIn('WORKSPACE_DATABASE_URL=${API_DB_SECRET}', workflow)
        self.assertNotIn(
            "WORKSPACE_DATABASE_URL=medlivo-team-staging-api-database-url:latest",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
