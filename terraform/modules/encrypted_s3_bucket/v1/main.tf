data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "bucket" {
  bucket = "${data.aws_caller_identity.current.account_id}-${var.env}-${var.bucket}"
  acl    = "private"
  tags   = {
    "johnk:category" = "${var.category}"
    "johnk:env"      = "${var.env}"
  }
  region = "${var.region}"
  versioning {
    enabled = "${var.versioning}"
  }
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm     = "AES256"
      }
    }
  }
}
