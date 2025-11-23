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

resource "aws_s3_bucket_lifecycle_configuration" "backup" {
  bucket = aws_s3_bucket.backup.bucket

  rule {
    id     = "restic-archive-data"
    status = "Enabled"

    filter {
      prefix = "archive/restic/data/"
    }

    transition {
      days = 3

      storage_class = "GLACIER_IR"
    }
  }

  rule {
    id     = "restic"
    status = "Enabled"

    filter {
      prefix = "restic/"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
