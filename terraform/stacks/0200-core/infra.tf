module "infra_s3_bucket" {
  source = "../../modules/kms_encrypted_s3_bucket/v1"

  bucket     = "infra"
  category   = "core"
  env        = local.env["name"]
  kms_key_id = data.terraform_remote_state.bootstrap.outputs.kms_key_id
  region     = local.env["default_aws_region"]
  versioning = "false"
}
