variable "project_id" {
  type        = string
  description = "Google Cloud project ID for Medlivo AI Platform."
}

variable "region" {
  type        = string
  description = "Primary Google Cloud region."
  default     = "us-west1"
}

variable "environment" {
  type        = string
  description = "Environment name."
  default     = "dev"
}

variable "db_tier" {
  type        = string
  description = "Cloud SQL machine tier."
  default     = "db-custom-2-7680"
}


variable "enable_phase3_staging_alerts" {
  type        = bool
  description = "Enable Phase 3 private-workspace alert resources. Resources are created only when environment is also staging."
  default     = false
}

variable "phase3_workspace_service_name" {
  type        = string
  description = "Cloud Run service name for the private Phase 3 workspace API in staging."
  default     = "medlivo-team-api-staging"
}

variable "phase3_alert_notification_channels" {
  type        = list(string)
  description = "Existing Cloud Monitoring notification channel resource names for Phase 3 staging alerts."
  default     = []
}
