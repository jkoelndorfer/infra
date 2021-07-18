module "infra_s3_bucket" {
  source = "../../modules/aws-kms-encrypted-s3-bucket/v1"

  bucket     = "infra"
  category   = "core"
  env        = local.env.name
  kms_key_id = data.terraform_remote_state.bootstrap.outputs.kms_key.id
  versioning = "false"
}
