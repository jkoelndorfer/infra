output "infra_mgmt_project" {
  description = "the created infra-mgmt project"
  value = {
    name       = google_project.infra_mgmt.name
    number     = google_project.infra_mgmt.number
    project_id = google_project.infra_mgmt.project_id
  }
}

output "terragrunt_service_account" {
  description = "service account used by terragrunt"
  value = {
    email = google_service_account.terragrunt.email
  }
}
