output "env_folder" {
  description = "folder containing environment-specific projects"
  value = {
    name         = google_folder.env_folder.name
    display_name = google_folder.env_folder.display_name
    env          = var.env_folder.env
    folder_id    = google_folder.env_folder.folder_id
  }
}
