module "s3_bucket" {
  source = "../../modules/aws-encrypted-s3-bucket/v1"

  bucket     = "backups"
  category   = "backup"
  env        = "${local.env["name"]}"
  versioning = "false"
}

module "ebs_volume" {
  source = "../../modules/aws-encrypted-ebs-volume/v1"

  availability_zone = "${local.env["default_aws_region"]}a"
  category          = "backup"
  env               = "${local.env["name"]}"
  name              = "syncthing-data"
  kms_key_arn       = "${data.terraform_remote_state.bootstrap.outputs.kms_key_arn}"
  role              = "syncthing"
  size              = local.env.backup_vol_size
  type              = "gp3"
}

# E-mail subscriptions are unsupported in Terraform because they must be confirmed
# by the e-mail address's owner. As such, we can't set the subscription up here.
# Since there is manual setup involved, this topic is a persistent resource.
#
# Don't forget to manually set up an SNS subscription! FeelsBadMan.
resource "aws_sns_topic" "backup_notifications" {
  name = "${local.env["name"]}-backup-notifications"
}
