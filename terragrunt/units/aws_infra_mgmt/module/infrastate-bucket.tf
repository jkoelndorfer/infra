resource "aws_s3_bucket" "infrastate" {
  bucket = var.infrastate_s3_bucket.bucket

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "infrastate" {
  bucket = aws_s3_bucket.infrastate.bucket

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "infrastate" {
  bucket = aws_s3_bucket.infrastate.bucket

  rule {
    id = "purge-old-versions"

    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days           = 7
      newer_noncurrent_versions = 20
    }
  }
}
