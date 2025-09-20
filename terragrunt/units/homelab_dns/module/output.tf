output "homelab_shared01_zone" {
  description = "the shared01 sub-zone used for homelab services"
  value       = module.homelab_shared01_zone
}

output "homelab_dns_project" {
  description = "the GCP project that homelab DNS zone(s) are configured in"
  value       = module.project
}

output "homelab_dns_updater_role" {
  description = "the custom role that grants access to update homelab DNS zone(s)"
  value = {
    id          = google_project_iam_custom_role.dns_record_updater.id
    permissions = google_project_iam_custom_role.dns_record_updater.permissions
    role_id     = google_project_iam_custom_role.dns_record_updater.role_id
  }
}
