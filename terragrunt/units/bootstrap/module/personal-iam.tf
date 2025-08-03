locals {
  # Roles granted to my personal account for day-to-day usage.
  personal_account_roles = [
    "roles/billing.viewer",
    "roles/iam.organizationRoleViewer",
    "roles/orgpolicy.policyViewer",
    "roles/resourcemanager.folderViewer",
    "roles/viewer",
  ]
}

resource "google_organization_iam_member" "personal_iam" {
  for_each = toset(local.personal_account_roles)

  org_id = var.gcp_organization.org_id
  role   = each.value
  member = var.gcp_personal_principal.member
}
