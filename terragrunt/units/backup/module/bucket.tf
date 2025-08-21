resource "google_storage_bucket" "backup" {
  project = module.project.project_id

  name     = "${var.env}-backup-${var.gcp_organization.org_id}"
  location = "US"

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  # For objects that change frequently, delete them if there
  # are sufficiently many newer versions.
  lifecycle_rule {
    condition {
      matches_storage_class = ["STANDARD"]
      with_state            = "ARCHIVED"
      num_newer_versions    = 15
    }

    action {
      type = "Delete"
    }
  }

  # If an object version exists in the standard storage
  # class for some time, we move it into nearline storage
  # where it will be maintained for a longer time.
  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 45
      matches_storage_class      = ["STANDARD"]
      with_state                 = "ARCHIVED"
    }

    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  # After objects hit nearline storage, require a larger number
  # of new versions before deletion. This ensures that object
  # versions which are "long-standing" survive pruning better.
  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 180
      matches_storage_class      = ["NEARLINE"]
      with_state                 = "ARCHIVED"
      num_newer_versions         = 25
    }

    action {
      type = "Delete"
    }
  }

  # This lifecycle rule is not expected to trigger.
  #
  # It'll clean up cruft if something weird happens.
  lifecycle_rule {
    condition {
      age = 2
    }

    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}
