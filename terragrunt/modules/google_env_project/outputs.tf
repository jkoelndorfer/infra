output "folder" {
  description = "the folder the project was created under"
  value       = var.google_env_folder
}

output "labels" {
  description = "the set of labels applied to the project"
  value       = terraform_data.after_project_service.output.project.labels
}

output "project_id" {
  description = "ID of the created project"
  value       = terraform_data.after_project_service.output.project.project_id
}

output "name" {
  description = "name of the created project"
  value       = terraform_data.after_project_service.output.project.name
}

output "number" {
  description = "number of the created project"
  value       = terraform_data.after_project_service.output.project.number
}
