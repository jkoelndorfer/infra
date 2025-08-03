locals {
  enforced_constraints = [
    # When new GCP projects are created, skip creating a default VPC network.
    "compute.skipDefaultNetworkCreation",

    # When new GCP projects are created, prevent default service accounts from
    # receiving the very broad "Editor" IAM grant.
    "iam.automaticIamGrantsForDefaultServiceAccounts",
    "iam.managed.preventPrivilegedBasicRolesForDefaultServiceAccounts",
  ]
}

resource "google_org_policy_policy" "enforced_constraint" {
  provider = google.infra

  for_each = toset(local.enforced_constraints)

  name   = "organizations/${var.gcp_organization.org_id}/policies/${each.value}"
  parent = "organizations/${var.gcp_organization.org_id}"

  spec {
    rules {
      enforce = "TRUE"
    }
  }

  depends_on = [
    google_project.infra_mgmt,
    google_project_service.infra_mgmt,
  ]
}
