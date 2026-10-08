locals {
  phase3_staging_alerts_enabled = var.environment == "staging" && var.enable_phase3_staging_alerts
}

resource "google_logging_metric" "phase3_workspace_database_failures" {
  count = local.phase3_staging_alerts_enabled ? 1 : 0

  name        = "medlivo-phase3-workspace-database-failures"
  description = "Event-only private workspace database/readiness failures in staging."

  filter = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.phase3_workspace_service_name}"
    (
      textPayload=~"workspace_(database_unavailable|readiness_database_unavailable)"
      OR jsonPayload.message=~"workspace_(database_unavailable|readiness_database_unavailable)"
    )
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }

  depends_on = [google_project_service.services]
}

resource "google_logging_metric" "phase3_workspace_access_denials" {
  count = local.phase3_staging_alerts_enabled ? 1 : 0

  name        = "medlivo-phase3-workspace-access-denials"
  description = "Authentication/authorization denial events for the private staging workspace."

  filter = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.phase3_workspace_service_name}"
    (
      textPayload=~"workspace_(authentication_denied|authorization_denied)"
      OR jsonPayload.message=~"workspace_(authentication_denied|authorization_denied)"
    )
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }

  depends_on = [google_project_service.services]
}

resource "google_monitoring_alert_policy" "phase3_workspace_database_failure" {
  count = local.phase3_staging_alerts_enabled ? 1 : 0

  display_name = "Medlivo Phase 3 staging workspace database failure"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Workspace database/readiness failure event"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.phase3_workspace_database_failures[0].name}\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = var.phase3_alert_notification_channels

  documentation {
    content   = "Private staging workspace emitted a sanitized database or readiness failure event. Keep the JobDiva pilot read-only/disabled as appropriate and follow docs/PHASE3_ROLLBACK_RUNBOOK.md."
    mime_type = "text/markdown"
  }

  depends_on = [google_project_service.services]
}

resource "google_monitoring_alert_policy" "phase3_workspace_access_denial_rate" {
  count = local.phase3_staging_alerts_enabled ? 1 : 0

  display_name = "Medlivo Phase 3 staging workspace access denial rate"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "10+ auth/authorization denials in five minutes"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.phase3_workspace_access_denials[0].name}\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GE"
      threshold_value = 10
      duration        = "0s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = var.phase3_alert_notification_channels

  documentation {
    content   = "Private staging workspace is seeing an elevated authentication/authorization denial rate. Review IAM, provisioned membership, OAuth configuration, and access logs without enabling bypasses."
    mime_type = "text/markdown"
  }

  depends_on = [google_project_service.services]
}

resource "google_monitoring_alert_policy" "phase3_workspace_http_5xx" {
  count = local.phase3_staging_alerts_enabled ? 1 : 0

  display_name = "Medlivo Phase 3 staging workspace HTTP 5xx"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "3+ Cloud Run 5xx responses in five minutes"

    condition_threshold {
      filter = <<-EOT
        resource.type="cloud_run_revision"
        resource.label."service_name"="${var.phase3_workspace_service_name}"
        metric.type="run.googleapis.com/request_count"
        metric.label."response_code_class"="5xx"
      EOT
      comparison      = "COMPARISON_GE"
      threshold_value = 3
      duration        = "0s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = var.phase3_alert_notification_channels

  documentation {
    content   = "Private staging workspace returned repeated HTTP 5xx responses. Check /ready, Cloud Run revision health, database reachability, and the Phase 3 rollback runbook."
    mime_type = "text/markdown"
  }

  depends_on = [google_project_service.services]
}
