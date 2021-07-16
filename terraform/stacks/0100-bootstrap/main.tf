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
  versioning      = true
}
