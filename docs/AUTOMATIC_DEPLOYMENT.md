# Automatic deployment

Pushing production application changes to `main` can automatically deploy Medlivo AI Platform to Cloud Run.

## Flow

1. GitHub authenticates to Google Cloud with Workload Identity Federation.
2. API image is built and pushed to Artifact Registry.
3. API deploys to Cloud Run with Cloud SQL and Secret Manager attached.
4. Recruiter web image is built against the deployed API URL.
5. Recruiter web deploys to Cloud Run.

No permanent Google service-account key is stored in GitHub.

## One-time setup

Run in Google Cloud Shell:

```bash
bash infrastructure/scripts/bootstrap-github-deploy.sh
```

The script prints two values.

In GitHub open:

Settings → Secrets and variables → Actions → Variables

Create:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`

After that, deployment is automatic for relevant pushes to `main`.

The workflow can also be run manually from GitHub Actions.
