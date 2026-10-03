# Google Cloud Setup

## Recommended project

Create a dedicated Google Cloud project for the Medlivo AI Platform rather than reusing the Ask Medlivo website-agent project.

Suggested project name:
`Medlivo AI Platform`

Suggested project ID pattern:
`medlivo-ai-platform-<unique suffix>`

Primary region:
`us-west1`

## One-time bootstrap

1. Create/select the project.
2. Confirm billing is attached.
3. Open Cloud Shell.
4. Clone `pks-alt/Medlivo-AI-Platform`.
5. Install/confirm Terraform.
6. Copy `infrastructure/terraform/terraform.tfvars.example` to `terraform.tfvars`.
7. Set the real project ID.
8. Run `terraform init`.
9. Run `terraform plan`.
10. Review the plan before `terraform apply`.

## After Terraform

Create secret versions for:
- JobDiva Client ID
- JobDiva username
- rotated JobDiva password
- database connection configuration

Do not use the JobDiva password previously pasted into chat. Rotate it first.

## First deploy order

1. Cloud SQL database + schema
2. API service to Cloud Run
3. recruiter-web service to Cloud Run
4. internal API connectivity
5. JobDiva connector proof
6. Pub/Sub workers
7. custom domain `recruit.medlivo.com`

## Notes

Cloud Run can connect to Cloud SQL using the Cloud SQL integration/Auth Proxy path. Secret Manager should be accessed with least-privilege IAM rather than embedding secrets in source code.
