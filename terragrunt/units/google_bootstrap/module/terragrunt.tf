resource "google_service_account" "terragrunt" {
  project      = google_project.infra_mgmt.project_id
  account_id   = "terragrunt"
  display_name = "Terragrunt"
  description  = "Service account used by Terragrunt to apply infrastructure changes"
}

# We don't use a google_service_account_key resource here
# because the key would be written to our version-controlled
# state file. Instead, we use a null_resource with a provisioner
# to create the key and save it locally.
resource "null_resource" "terragrunt_key" {
  provisioner "local-exec" {
    command = "gcloud iam service-accounts keys create ${var.paths.google_credentials} --iam-account ${google_service_account.terragrunt.email}"
  }
}

resource "google_organization_iam_member" "terragrunt_folder_creator" {
  org_id = var.google_organization.org_id
  role   = "roles/resourcemanager.folderCreator"
  member = google_service_account.terragrunt.member
}

resource "google_organization_iam_member" "terragrunt_project_creator" {
  org_id = var.google_organization.org_id
  role   = "roles/resourcemanager.projectCreator"
  member = google_service_account.terragrunt.member
}

resource "google_project_iam_member" "terragrunt_infra_mgmt_secret_reader" {
  project = google_project.infra_mgmt.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = google_service_account.terragrunt.member
}

resource "google_project_iam_member" "terragrunt_service_consumer" {
  project = google_project.infra_mgmt.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = google_service_account.terragrunt.member
}

resource "google_project_iam_member" "terragrunt_infra_mgmt_monitoring_channel_editor" {
  project = google_project.infra_mgmt.project_id
  role    = "roles/monitoring.notificationChannelEditor"
  member  = google_service_account.terragrunt.member
}

resource "google_billing_account_iam_member" "terragrunt_cost_manager" {
  billing_account_id = var.google_billing_account.id

  role   = "roles/billing.costsManager"
  member = google_service_account.terragrunt.member
}

resource "google_storage_bucket_iam_member" "terragrunt_state_bucket_viewer" {
  bucket = google_storage_bucket.infrastate.name
  role   = "roles/storage.bucketViewer"
  member = google_service_account.terragrunt.member
}

# Required to allow Terragrunt to associate newly created projects with
# the primary billing account.
#
# See https://cloud.google.com/billing/docs/how-to/billing-access.
resource "google_billing_account_iam_member" "terragrunt_billing" {
  billing_account_id = var.google_billing_account.id

  role   = "roles/billing.user"
  member = google_service_account.terragrunt.member
}

locals {
  infrastate_bucket_resource_name = "projects/_/buckets/${google_storage_bucket.infrastate.name}"

  terragrunt_state_iam_bucket_conditions = join(" && ", [
    "resource.type == 'storage.googleapis.com/Bucket'",
    "resource.name == '${local.infrastate_bucket_resource_name}'",
  ])

  terragrunt_state_iam_object_conditions = join(" && ", [
    "resource.type == 'storage.googleapis.com/Object'",
    "resource.name.startsWith('${local.infrastate_bucket_resource_name}/objects/terragrunt/')",
  ])
}

resource "google_storage_bucket_iam_member" "terragrunt_state_file_access" {
  bucket = google_storage_bucket.infrastate.name
  role   = "roles/storage.objectUser"
  member = google_service_account.terragrunt.member

  condition {
    title       = "Terragrunt State Access Only"
    description = "limit bucket access to only Terragrunt state files"
    expression  = "(${local.terragrunt_state_iam_bucket_conditions}) || (${local.terragrunt_state_iam_object_conditions})"
  }
}
