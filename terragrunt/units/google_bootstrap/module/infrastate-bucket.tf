resource "google_storage_bucket" "infrastate" {
  name     = var.infrastate_gcs_bucket.name
  project  = google_project.infra_mgmt.project_id
  location = "US"

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }
}
