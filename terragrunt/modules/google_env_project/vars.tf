variable "google_env_folder" {
  type = object({
    env       = string
    folder_id = string
  })
  description = "the environment folder that the project will be created in"
}

variable "function" {
  type        = string
  description = "an identifier label for the project's purpose; used as an alternative to remote state to look up a project ID"

  validation {
    condition     = can(regex("^[a-z0-9-]{1,20}$", var.function))
    error_message = "Function must contain lowercase letters, numbers, and dashes with a maximum of 20 characters"
  }
}

variable "services" {
  type        = list(string)
  description = "list of GCP APIs to enable for the project"
  default     = []
}
