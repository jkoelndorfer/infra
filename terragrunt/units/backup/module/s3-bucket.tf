resource "aws_s3_bucket" "backup" {
  bucket = "${var.env}-backup-${var.aws_organization.master_account_id}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "backup" {
  bucket = aws_s3_bucket.backup.bucket

  block_public_acls   = true
  block_public_policy = true
  ignore_public_acls  = true

  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "backup" {
  bucket = aws_s3_bucket.backup.bucket

  versioning_configuration {
    status = "Enabled"
  }
}

locals {
  syncthing_prefix = "syncthing/"
}

resource "aws_s3_bucket_lifecycle_configuration" "backup" {
  bucket = aws_s3_bucket.backup.bucket

  rule {
    id     = "deep-archive"
    status = "Enabled"

    filter {
      prefix = "deep-archive/"
    }

    transition {
      days = 1

      storage_class = "DEEP_ARCHIVE"
    }
  }

  rule {
    id     = "syncthing-storage-class"
    status = "Enabled"

    filter {
      prefix = local.syncthing_prefix
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }
  }

  rule {
    id     = "syncthing-7-day"
    status = "Enabled"

    filter {
      prefix = local.syncthing_prefix
    }

    noncurrent_version_expiration {
      noncurrent_days = 7

      newer_noncurrent_versions = 30
    }
  }

  rule {
    id     = "syncthing-90-day"
    status = "Enabled"

    filter {
      prefix = local.syncthing_prefix
    }

    noncurrent_version_expiration {
      noncurrent_days = 90

      newer_noncurrent_versions = 5
    }
  }

  rule {
    id     = "syncthing-1-year"
    status = "Enabled"

    filter {
      prefix = local.syncthing_prefix
    }

    noncurrent_version_expiration {
      noncurrent_days = 365

      newer_noncurrent_versions = 3
    }
  }

  rule {
    id     = "syncthing-2-year"
    status = "Enabled"

    filter {
      prefix = local.syncthing_prefix
    }

    noncurrent_version_expiration {
      noncurrent_days = 730
    }
  }

  rule {
    id     = "photoprism"
    status = "Enabled"

    filter {
      prefix = "photoprism/"
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }

    transition {
      days = 0

      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "vaultwarden"
    status = "Enabled"

    filter {
      prefix = "vaultwarden/"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365

      newer_noncurrent_versions = 100
    }
  }
}
