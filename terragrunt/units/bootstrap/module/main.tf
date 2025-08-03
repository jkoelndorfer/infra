locals {
  project_name = "infra-mgmt"
}

resource "random_string" "project_id_suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = false
  special = false
}

resource "google_project" "infra_mgmt" {
  name            = local.project_name
  project_id      = "${local.project_name}-${random_string.project_id_suffix.result}"
  org_id          = var.gcp_organization_id
  billing_account = var.gcp_billing_account_id
}

resource "google_storage_bucket" "tf_state" {
  name     = var.tfstate_gcs_bucket
  project  = google_project.infra_mgmt.project_id
  location = "US"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}
