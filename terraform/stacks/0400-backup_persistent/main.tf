data "terraform_remote_state" "bootstrap" {
  backend = "local"
  config {
    path = "../bootstrap/terraform.tfstate.d/prod/terraform.tfstate"
  }
}

data "terraform_remote_state" "core" {
  backend   = "s3"
  workspace = "${terraform.workspace}"
  config {
    bucket               = "310987624463-prod-tfstate"
    key                  = "core.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}

module "s3_bucket" {
  source = "../../modules/encrypted_s3_bucket/v1"

  bucket     = "backups"
  category   = "backup"
  env        = "${local.env["name"]}"
  region     = "${local.env["default_aws_region"]}"
  versioning = "false"
}

module "ebs_volume" {
  source = "../../modules/encrypted_ebs_volume/v1"

  availability_zone = "${local.env["default_aws_region"]}a"
  category          = "backup"
  class             = "syncthing"
  env               = "${local.env["name"]}"
  name              = "syncthing-data"
  kms_key_arn       = "${data.terraform_remote_state.bootstrap.kms_key_arn}"
  size              = "500"
  type              = "sc1"
}

# E-mail subscriptions are unsupported in Terraform because they must be confirmed
# by the e-mail address's owner. As such, we can't set the subscription up here.
# Since there is manual setup involved, this topic is a persistent resource.
#
# Don't forget to manually set up an SNS subscription! FeelsBadMan.
resource "aws_sns_topic" "backup_notifications" {
  name = "${local.env["name"]}-backup-notifications"
}
