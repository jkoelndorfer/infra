variable "infrastate_gcs_bucket" {
  type        = object({ name = string })
  description = "the name of the GCS bucket containing Terraform/OpenTofu state files"
}
