resource "google_folder" "env_folder" {
  display_name = var.env
  parent       = "organizations/${var.gcp_organization_id}"
}
