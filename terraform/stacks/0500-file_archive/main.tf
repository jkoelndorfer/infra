resource "aws_s3_bucket" "archive" {
  bucket = "${local.aws_account_id}-file-archive-${local.env.name}"
  acl    = "private"

  versioning {
    enabled = false
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = data.terraform_remote_state.bootstrap.outputs.kms_key_id
        sse_algorithm     = "aws:kms"
      }
    }
  }

  tags = {
    Name             = "file-archive-${local.env.name}"
    "johnk:env"      = local.env.name
    "johnk:category" = "file-archive"
  }

  lifecycle_rule {
    id      = "glacier"
    enabled = true
    prefix  = "glacier/"

    transition {
      days = 1
      storage_class = "GLACIER"
    }
  }
}
