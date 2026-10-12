import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]


class DeploymentMigrationTests(unittest.TestCase):
    def test_api_image_packages_workspace_migrations(self):
        dockerfile = (ROOT / "infrastructure/team-staging/Dockerfile.api").read_text()
        self.assertIn("COPY services/team-workspace/migrations ./migrations", dockerfile)

    def test_staging_deploy_applies_reviewed_migration_before_promotion(self):
        workflow = (ROOT / ".github/workflows/deploy-team-staging.yml").read_text()
        migration = "014_job_content_standards.sql"
        self.assertIn("Apply reviewed workspace migration 014", workflow)
        self.assertIn(migration, workflow)
        self.assertLess(
            workflow.index("Apply reviewed workspace migration 014"),
            workflow.index("Deploy private API candidate with schema readiness gate"),
        )
        self.assertIn("medlivo-team-staging-api-database-url:latest", workflow)
        self.assertIn("--set-cloudsql-instances", workflow)


if __name__ == "__main__":
    unittest.main()
