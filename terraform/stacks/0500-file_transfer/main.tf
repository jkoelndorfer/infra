locals {
  index_document = "index.html"
  error_document = "error.html"
}

resource "aws_s3_bucket" "file_transfer" {
  bucket = "${local.aws_account_id}-file-transfer-${local.env.name}"
  acl    = "private"

  website {
    index_document = local.index_document
    error_document = local.error_document
  }

  tags = {
    Name             = "file-transfer-${local.env.name}"
    "johnk:env"      = local.env.name
    "johnk:category" = "file-transfer"
  }

  lifecycle_rule {
    id      = "secure"
    enabled = true
    prefix  = "secure/"

    expiration {
      days = 3
    }
  }
}

resource "aws_s3_bucket_object" "index" {
  bucket       = aws_s3_bucket.file_transfer.bucket
  key          = local.index_document
  acl          = "public-read"
  content      = ""
  content_type = "text/plain"
}

resource "aws_s3_bucket_object" "error" {
  bucket       = aws_s3_bucket.file_transfer.bucket
  key          = local.error_document
  acl          = "public-read"
  content      = ""
  content_type = "text/plain"
}
