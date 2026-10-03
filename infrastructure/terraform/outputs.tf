output "cloud_sql_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "api_service_account" {
  value = google_service_account.api.email
}

output "recruiter_web_service_account" {
  value = google_service_account.recruiter_web.email
}

output "workers_service_account" {
  value = google_service_account.workers.email
}

output "documents_bucket" {
  value = google_storage_bucket.documents.name
}

output "events_topic" {
  value = google_pubsub_topic.platform_events.name
}

output "analytics_dataset" {
  value = google_bigquery_dataset.analytics.dataset_id
}

output "artifact_registry_repository" {
  value = google_artifact_registry_repository.containers.repository_id
}
