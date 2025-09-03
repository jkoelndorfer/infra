data "google_secret_manager_secret_version_access" "cloud_billing_alerts" {
  project = var.google_infra_mgmt_project.project_id

  secret = "cloud-billing-alerts"
}

locals {
  cloud_billing_alerts = jsondecode(data.google_secret_manager_secret_version_access.cloud_billing_alerts.secret_data)
}
