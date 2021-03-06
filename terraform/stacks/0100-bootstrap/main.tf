provider "aws" {
    region = local.env["default_aws_region"]
    # Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in the environment
    version = "~> 2.16"
}

resource "aws_kms_key" "enc" {
  description = "kms key used for general encryption"
  lifecycle {
    prevent_destroy = true
  }
  tags = {
    "johnk:category" = "core"
    "johnk:env"      = local.env["name"]
  }
}

module "bucket" {
  source = "../../modules/aws-kms-encrypted-s3-bucket/v1"

  bucket          = "tfstate"
  category        = "core"
  env             = local.env["name"]
  kms_key_id      = aws_kms_key.enc.id
  region          = local.env["default_aws_region"]
  versioning      = true
}
