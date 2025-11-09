variable "env" {
  description = "environment that infrastructure is being deployed into, e.g. 'dev' or 'prod'"
  type        = string
}

variable "google_env_folder" {
  description = "folder containing environment-specific projects"
  type = object({
    name         = string
    display_name = string
    env          = string
    folder_id    = string
  })
}
