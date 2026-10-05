#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="medlivo-ai-platform"
PROJECT_NUMBER="363168336964"
REGION="us-west1"
REPOSITORY="pks-alt/Medlivo-AI-Platform"
POOL_ID="github-actions"
PROVIDER_ID="github"
DEPLOYER_SA="github-deployer"

gcloud config set project "$PROJECT_ID"

gcloud services enable   iamcredentials.googleapis.com   sts.googleapis.com   artifactregistry.googleapis.com   run.googleapis.com

if ! gcloud artifacts repositories describe medlivo-ai-containers --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create medlivo-ai-containers     --repository-format=docker     --location="$REGION"     --description="Medlivo AI Platform containers"
fi

if ! gcloud iam service-accounts describe "${DEPLOYER_SA}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$DEPLOYER_SA"     --display-name="GitHub Cloud Run Deployer"
fi

DEPLOYER_EMAIL="${DEPLOYER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

for ROLE in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID"     --member="serviceAccount:${DEPLOYER_EMAIL}"     --role="$ROLE"     --quiet
done

if ! gcloud iam workload-identity-pools describe "$POOL_ID" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL_ID"     --location=global     --display-name="GitHub Actions"
fi

if ! gcloud iam workload-identity-pools providers describe "$PROVIDER_ID"   --workload-identity-pool="$POOL_ID"   --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID"     --location=global     --workload-identity-pool="$POOL_ID"     --display-name="GitHub"     --issuer-uri="https://token.actions.githubusercontent.com/"     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner"     --attribute-condition="assertion.repository=='${REPOSITORY}'"
fi

POOL_NAME="$(gcloud iam workload-identity-pools describe "$POOL_ID" --location=global --format='value(name)')"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_EMAIL"   --role="roles/iam.workloadIdentityUser"   --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${REPOSITORY}"   --quiet

PROVIDER_NAME="$(gcloud iam workload-identity-pools providers describe "$PROVIDER_ID"   --workload-identity-pool="$POOL_ID"   --location=global   --format='value(name)')"

echo
echo "Bootstrap complete."
echo "GCP_WORKLOAD_IDENTITY_PROVIDER=${PROVIDER_NAME}"
echo "GCP_DEPLOY_SERVICE_ACCOUNT=${DEPLOYER_EMAIL}"


# RUNTIME SERVICE ACCOUNT PERMISSIONS
API_SA="medlivo-ai-api@${PROJECT_ID}.iam.gserviceaccount.com"
WEB_SA="medlivo-recruit-web@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$API_SA" >/dev/null 2>&1; then
  gcloud iam service-accounts create medlivo-ai-api \
    --display-name="Medlivo AI API"
fi

# Allow GitHub deployer to attach the runtime service accounts to Cloud Run.
for TARGET_SA in "$API_SA" "$WEB_SA"; do
  gcloud iam service-accounts add-iam-policy-binding "$TARGET_SA"     --member="serviceAccount:${DEPLOYER_EMAIL}"     --role="roles/iam.serviceAccountUser"     --quiet
done

# API runtime permissions.
gcloud projects add-iam-policy-binding "$PROJECT_ID"   --member="serviceAccount:${API_SA}"   --role="roles/cloudsql.client"   --quiet

if gcloud secrets describe medlivo-ai-database-url >/dev/null 2>&1; then
  gcloud secrets add-iam-policy-binding medlivo-ai-database-url     --member="serviceAccount:${API_SA}"     --role="roles/secretmanager.secretAccessor"     --quiet
fi

echo
echo "Runtime service-account permissions configured."
