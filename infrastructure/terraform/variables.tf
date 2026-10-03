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
