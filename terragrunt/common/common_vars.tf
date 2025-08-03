variable "env" {
  type        = string
  description = "the environment that infrastructure is being deployed to, e.g. 'dev' or 'prod'"
}

variable "gcp_billing_account_id" {
  type        = string
  description = "the ID of the GCP billing account that infrastructure is billed to"
}

variable "gcp_organization_id" {
  type        = string
  description = "the ID of the GCP organization that infrastructure is being deployed to"
}
