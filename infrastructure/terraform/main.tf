provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  prefix = "medlivo-ai-${var.environment}"

  required_services = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ])
}

resource "google_project_service" "services" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "api" {
  account_id   = "${local.prefix}-api"
  display_name = "Medlivo AI Platform API"
}

resource "google_service_account" "recruiter_web" {
  account_id   = "${local.prefix}-web"
  display_name = "Medlivo Recruit Web"
}

resource "google_service_account" "workers" {
  account_id   = "${local.prefix}-workers"
  display_name = "Medlivo AI Platform Workers"
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.prefix}-postgres"
  database_version = "POSTGRES_17"
  region           = var.region

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
    }

    ip_configuration {
      ipv4_enabled = true
    }
  }

  deletion_protection = true

  depends_on = [google_project_service.services]
}

resource "google_sql_database" "app" {
  name     = "medlivo_ai"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  name     = "medlivo_app"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

resource "google_secret_manager_secret" "jobdiva_client_id" {
  secret_id = "${local.prefix}-jobdiva-client-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret" "jobdiva_username" {
  secret_id = "${local.prefix}-jobdiva-username"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "jobdiva_password" {
  secret_id = "${local.prefix}-jobdiva-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "${local.prefix}-database-url"

  replication {
    auto {}
  }
}

resource "google_pubsub_topic" "platform_events" {
  name = "${local.prefix}-events"

  depends_on = [google_project_service.services]
}

resource "google_pubsub_subscription" "platform_events_workers" {
  name  = "${local.prefix}-events-workers"
  topic = google_pubsub_topic.platform_events.name

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 10
  }
}

resource "google_pubsub_topic" "dead_letter" {
  name = "${local.prefix}-dead-letter"
}

resource "google_storage_bucket" "documents" {
  name                        = "${var.project_id}-medlivo-documents-${var.environment}"
  location                    = var.region
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 3650
    }

    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_bigquery_dataset" "analytics" {
  dataset_id = "medlivo_ai_${var.environment}"
  location   = "US"

  delete_contents_on_destroy = false

  depends_on = [google_project_service.services]
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "${local.prefix}-containers"
  format        = "DOCKER"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "workers_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.workers.email}"
}

resource "google_storage_bucket_iam_member" "workers_documents" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.workers.email}"
}
