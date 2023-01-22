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
        sse_algorithm = "AES256"
      }
    }
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_rules
    iterator = l

    content {
      id      = l.value.id
      prefix  = l.value.prefix
      enabled = true

      dynamic "transition" {
        for_each = l.value.transitions
        iterator = t

        content {
          days          = t.value.days
          storage_class = t.value.storage_class
        }
      }

      dynamic "noncurrent_version_transition" {
        for_each = l.value.noncurrent_version_transitions
        iterator = t

        content {
          days          = t.value.days
          storage_class = t.value.storage_class
        }
      }

      dynamic "noncurrent_version_expiration" {
        for_each = [l.value.noncurrent_version_expiration]
        iterator = e

        content {
          days = e.value.days
        }
      }
    }
  }
}
