resource "google_service_account" "homelab_backup" {
  project = module.project.project_id

  account_id   = "homelab-backup"
  display_name = "Homelab Backup"
}

resource "google_service_account_key" "homelab_backup" {
  service_account_id = google_service_account.homelab_backup.name
}

resource "google_storage_bucket_iam_member" "homelab_access" {
  bucket = google_storage_bucket.backup.bucket
  role   = "TODO"
  member = google_service_account.homelab_backup.member

  condition {
    title      = "Prevent Modifying Noncurrent Objects"
    expression = "api.getAttribute('storage.googleapis.com/', '') == ''"
  }
}
