data "aws_caller_identity" "current" {}

data "aws_ami" "syncthing" {
  most_recent = true
  filter {
    name = "name"
    values = ["${local.env["syncthing_ami"]}"]
  }
  owners = ["${data.aws_caller_identity.current.account_id}"]
}

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

data "terraform_remote_state" "backup_persistent" {
  backend   = "s3"
  workspace = "${terraform.workspace}"
  config {
    bucket               = "310987624463-prod-tfstate"
    key                  = "backup_persistent.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}

resource "aws_subnet" "default" {
  vpc_id            = "${data.terraform_remote_state.core.vpc_id}"
  availability_zone = "${data.terraform_remote_state.backup_persistent.ebs_volume_az}"
  cidr_block        = "${cidrsubnet(data.terraform_remote_state.core.vpc_cidr_block, 8, local.env["backup_subnet_num"])}"

  tags = {
    "Name"           = "${local.env["name"]}-backup-infra"
    "johnk:category" = "backup"
    "johnk:env"      = "${local.env["name"]}"
  }
}

resource "aws_security_group" "syncthing" {
  name = "${local.env["name"]}-syncthing"
  description = "Security group for syncthing instances"
  vpc_id = "${data.terraform_remote_state.core.vpc_id}"

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port = "${local.syncthing_port}"
    to_port = "${local.syncthing_port}"
    protocol = "tcp"
  }

  tags = {
    "Name" = "${local.env["name"]}-syncthing"
    "johnk:category" = "backup"
    "johnk:env" = "${local.env["name"]}"
  }
}

module "ec2_role" {
  source = "../../modules/ec2_role/v1"

  env  = "${local.env["name"]}"
  name = "syncthing"
}

module "asg" {
  source = "../../modules/asg/v1"

  associate_public_ip_address = "true"
  category                    = "backup"
  class                       = "syncthing"
  desired_capacity            = 1
  dns                         = "syncthing.${local.env["dns_zone"]}"
  env                         = "${local.env["name"]}"
  iam_instance_profile        = "${module.ec2_role.iam_instance_profile_name}"
  image_id                    = "${data.aws_ami.syncthing.id}"
  instance_type               = "t3.micro"
  max_size                    = 1
  min_size                    = 0
  name                        = "syncthing"
  security_groups             = ["${aws_security_group.syncthing.id}"]
  subnet_ids                  = ["${aws_subnet.default.id}"]
}

resource "aws_autoscaling_schedule" "backup_schedule" {
  autoscaling_group_name = "${module.asg.asg_name}"
  scheduled_action_name  = "${local.env["name"]}-nightly-backup"
  # Schedule is in UTC
  recurrence             = "0 8 * * *"
  min_size               = -1
  max_size               = -1
  desired_capacity       = 1
}

resource "aws_iam_role_policy" "backup_ec2_policy" {
  name = "${local.env["name"]}-syncthing-backup"
  role = "${module.ec2_role.iam_role_name}"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": "ec2:AttachVolume",
            "Resource": [
              "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:volume/*",
              "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:instance/*"
            ],
            "Condition": {
              "StringEquals": {
                "ec2:ResourceTag/johnk:class": "syncthing"
              }
            }
        },
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": "kms:CreateGrant",
            "Resource": "${data.terraform_remote_state.bootstrap.kms_key_arn}",
            "Condition": {
              "Bool": {
                "kms:GrantIsForAWSResource": true
              },
              "ForAllValues:StringEquals": {
                "kms:GrantOperations": [
                  "Decrypt",
                  "Encrypt"
                ]
              }
            }
        },
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameterByPath",
                "ssm:GetParameters"
            ],
            "Resource": "arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter/${local.env["name"]}/backup/*"
        },
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucketMultipartUploads",
                "s3:AbortMultipartUpload",
                "s3:ListBucket",
                "s3:DeleteObject",
                "s3:ListMultipartUploadParts"
            ],
            "Resource": [
              "${data.terraform_remote_state.backup_persistent.s3_bucket_arn}",
              "${data.terraform_remote_state.backup_persistent.s3_bucket_arn}/*"
            ]
        },
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": "autoscaling:UpdateAutoScalingGroup",
            "Resource": "${module.asg.asg_arn}"
        },
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": "sns:Publish",
            "Resource": "${data.terraform_remote_state.backup_persistent.sns_topic_arn}"
        }
    ]
}
EOF
}

resource "aws_ssm_parameter" "ebs_volume_id" {
  name  = "/${local.env["name"]}/backup/syncthing_ebs_volume_id"
  type  = "String"
  value = "${data.terraform_remote_state.backup_persistent.ebs_volume_id}"
}

resource "aws_ssm_parameter" "backup_s3_bucket" {
  name  = "/${local.env["name"]}/backup/backup_s3_bucket"
  type  = "String"
  value = "${data.terraform_remote_state.backup_persistent.s3_bucket_id}"
}

resource "aws_ssm_parameter" "backup_sns_topic_arn" {
  name  = "/${local.env["name"]}/backup/backup_sns_topic_arn"
  type  = "String"
  value = "${data.terraform_remote_state.backup_persistent.sns_topic_arn}"
}
