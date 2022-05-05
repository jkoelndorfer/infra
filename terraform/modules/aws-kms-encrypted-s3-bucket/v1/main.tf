data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "bucket" {
  bucket = "${data.aws_caller_identity.current.account_id}-${var.bucket}-${var.env}"
  acl    = "private"
  tags = {
    "johnk:category" = var.category
    "johnk:env"      = var.env
  }
  versioning {
    enabled = var.versioning
  }
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm     = "aws:kms"
        kms_master_key_id = var.kms_key_id
      }
    }
  }
}
