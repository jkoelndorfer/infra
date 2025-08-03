locals {
  project_name = "infra-mgmt"

  project_services = [
    # This is needed by the Terragrunt service account to associate projects
    # to a billing account.
    "cloudbilling.googleapis.com",

    # This is needed by the Terragrunt service account to create folders and projects.
    "cloudresourcemanager.googleapis.com",

    # This is needed by Terragrunt to enable the v2 organization policy API.
    "orgpolicy.googleapis.com",

    # This is needed to enable Secret Manager secret creation in infra-mgmt.
    "secretmanager.googleapis.com",

    # This is needed so that Terragrunt can enable APIs on projects it creates.
    # See https://github.com/hashicorp/terraform-provider-google/issues/1538#issuecomment-392127015.
    "serviceusage.googleapis.com",
  ]
}

# The infra-mgmt project may be used as a default quota project for some
# API calls. Using dynamically-generated data for Terraform providers
# is tricky, so instead of using a random suffix like we do for most
# projects, this project uses our organization ID (a constant), as
# a suffix so it can be easily referenced for API quota purposes.
resource "google_project" "infra_mgmt" {
  name            = local.project_name
  project_id      = "${local.project_name}-${var.gcp_organization.org_id}"
  org_id          = var.gcp_organization.org_id
  billing_account = var.gcp_billing_account.id
  labels = {
    function = "infra-mgmt"
  }
}

resource "google_project_service" "infra_mgmt" {
  for_each = toset(local.project_services)

  project = google_project.infra_mgmt.project_id
  service = each.value
}
