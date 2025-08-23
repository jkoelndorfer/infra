variable "function" {
  type        = string
  description = "an identifier tag for the account's purpose"
}

variable "env" {
  type        = string
  description = "the environment that the account is deployed in, e.g. 'root', 'dev', or 'prod'"

  validation {
    condition     = contains(["bootstrap", "dev", "prod"], var.env)
    error_message = "Environment must be 'bootstrap', 'dev', or 'prod'"
  }
}
