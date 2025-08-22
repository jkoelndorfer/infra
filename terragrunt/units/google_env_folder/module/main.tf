resource "google_folder" "env_folder" {
  display_name = var.google_env_folder.env
  parent       = "organizations/${var.gcp_organization.org_id}"
}
