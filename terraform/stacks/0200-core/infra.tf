data "terraform_remote_state" "bootstrap" {
  backend = "local"
  config {
    path = "../bootstrap/terraform.tfstate.d/prod/terraform.tfstate"
  }
}

module "infra_s3_bucket" {
  source = "../../modules/kms_encrypted_s3_bucket/v1"

  bucket     = "infra"
  category   = "core"
  env        = "${local.env["name"]}"
  kms_key_id = "${data.terraform_remote_state.bootstrap.kms_key_id}"
  region     = "${local.env["default_aws_region"]}"
  versioning = "false"
}
