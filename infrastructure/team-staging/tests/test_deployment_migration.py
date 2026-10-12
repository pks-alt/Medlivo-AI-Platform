import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]


class DeploymentMigrationTests(unittest.TestCase):
    def test_api_image_packages_workspace_migrations(self):
        dockerfile = (ROOT / "infrastructure/team-staging/Dockerfile.api").read_text()
        self.assertIn("COPY services/team-workspace/migrations ./migrations", dockerfile)

    def test_staging_deploy_uses_migration_only_identity_before_promotion(self):
        workflow = (ROOT / ".github/workflows/deploy-team-staging.yml").read_text()
        migration = "014_job_content_standards.sql"
        self.assertIn("Verify staging migration identity", workflow)
        self.assertIn("medlivo-team-schema-staging@", workflow)
        self.assertIn("medlivo-team-staging-migration-database-url:latest", workflow)
        self.assertNotIn(
            "WORKSPACE_DATABASE_URL=medlivo-team-staging-api-database-url:latest",
            workflow,
        )
        self.assertIn("Apply reviewed workspace migration 014", workflow)
        self.assertIn(migration, workflow)
        self.assertLess(
            workflow.index("Apply reviewed workspace migration 014"),
            workflow.index("Deploy private API candidate with schema readiness gate"),
        )
        self.assertIn("--set-cloudsql-instances", workflow)

    def test_release_sha_is_stamped_and_verified(self):
        workflow = (ROOT / ".github/workflows/deploy-team-staging.yml").read_text()
        self.assertGreaterEqual(workflow.count("MEDLIVO_RELEASE_SHA"), 4)
        self.assertIn("Verify deployed release SHA", workflow)
        self.assertIn("STAGING_RELEASE_SHA=${GITHUB_SHA}", workflow)


if __name__ == "__main__":
    unittest.main()
