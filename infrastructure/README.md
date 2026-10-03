# Infrastructure

Google Cloud is the Phase 1 platform, but services remain containerized and portable.

## Provisioned by Terraform

The initial Terraform scaffold covers:

- required Google Cloud APIs
- dedicated service accounts for API, recruiter web, and workers
- Cloud SQL for PostgreSQL
- Pub/Sub event topic + worker subscription + dead-letter topic
- Secret Manager secret containers
- Cloud Storage document bucket
- BigQuery analytics dataset
- Artifact Registry
- initial least-privilege IAM bindings

## Deliberately not provisioned yet

- production Cloud Run services
- custom domain mapping for recruit.medlivo.com
- VPC/private IP design
- vector database/search provider
- CI/CD pipelines
- environment separation beyond the current variable
- production database sizing/HA

Those should follow after the first API/database deployment is validated.

## Security principles

- no JobDiva credentials in GitHub
- credentials belong in Secret Manager
- separate service accounts by workload
- least privilege
- Cloud SQL access only for services that need it
- audit/logging enabled at the platform level

## Local development

Use `compose.yaml` for PostgreSQL.

## Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Do not add real secret values to Terraform state. Create secret versions separately after resources exist.
