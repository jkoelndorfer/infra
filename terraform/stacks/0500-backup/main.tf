data "aws_ami" "syncthing" {
  most_recent = true
  filter {
    name   = "name"
    values = [local.env["syncthing_ami"]]
  }
  owners = [data.aws_caller_identity.current.account_id]
}

resource "aws_subnet" "default" {
  vpc_id            = data.terraform_remote_state.core.outputs.vpc_id
  availability_zone = data.terraform_remote_state.backup_persistent.outputs.ebs_volume_az
  cidr_block        = cidrsubnet(data.terraform_remote_state.core.outputs.vpc_cidr_block, 8, local.env["backup_subnet_num"])

  tags = {
    "Name"           = "${local.env["name"]}-backup-infra"
    "johnk:category" = "backup"
    "johnk:env"      = local.env["name"]
  }
}

resource "aws_security_group" "syncthing" {
  name        = "${local.env["name"]}-syncthing"
  description = "Security group for syncthing instances"
  vpc_id      = data.terraform_remote_state.core.outputs.vpc_id

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = local.syncthing_port
    to_port     = local.syncthing_port
    protocol    = "tcp"
  }

  tags = {
    "Name"           = "${local.env["name"]}-syncthing"
    "johnk:category" = "backup"
    "johnk:env"      = local.env["name"]
  }
}

module "ec2_role" {
  source = "../../modules/aws-ec2-role/v1"

  env  = local.env["name"]
  name = "syncthing"
}

module "asg" {
  source = "../../modules/aws-ec2-asg/v1"

  associate_public_ip_address = "true"
  category                    = "backup"
  role                        = "syncthing"
  desired_capacity            = 1
  dns                         = "syncthing-cloud.${local.env["dns_zone"]}"
  env                         = local.env["name"]
  iam_instance_profile        = module.ec2_role.iam_instance_profile_name
  image_id                    = data.aws_ami.syncthing.id
  instance_type               = "t3.micro"
  max_size                    = 1
  min_size                    = 0
  name                        = "syncthing"
  security_groups             = [aws_security_group.syncthing.id]
  subnet_ids                  = [aws_subnet.default.id]
}

resource "aws_autoscaling_schedule" "backup_schedule" {
  autoscaling_group_name = module.asg.asg_name
  scheduled_action_name  = "${local.env["name"]}-nightly-backup"
  # Schedule is in UTC
  recurrence       = "0 8 * * *"
  min_size         = -1
  max_size         = -1
  desired_capacity = 1
}

data "aws_iam_policy_document" "backup_ec2_policy" {
  statement {
    effect    = "Allow"
    actions   = ["ec2:AttachVolume"]
    resources = [
      "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:volume/*",
      "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:instance/*",
    ]
    condition {
      test     = "StringEquals"
      variable = "ec2:ResourceTag/johnk:role"
      values   = ["syncthing"]
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["kms:CreateGrant"]
    resources = [data.terraform_remote_state.bootstrap.outputs.kms_key_arn]
    condition {
      test     = "Bool"
      variable = "kms:GrantIsForAWSResource"
      values   = [true]
    }
    condition {
      test     = "ForAllValues:StringEquals"
      variable = "kms:GrantOperations"
      values   = ["Decrypt", "Encrypt"]
    }
  }

  statement {
    effect    = "Allow"
    actions   = [
      "ssm:GetParameter",
      "ssm:GetParameterByPath",
      "ssm:GetParameters",
    ]
    resources = ["arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter/${local.env["name"]}/backup/*"]
  }

  statement {
    effect    = "Allow"
    actions   = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucketMultipartUploads",
      "s3:AbortMultipartUpload",
      "s3:ListBucket",
      "s3:DeleteObject",
      "s3:ListMultipartUploadParts",
    ]
    resources = [
      data.terraform_remote_state.backup_persistent.outputs.s3_bucket_arn,
      "${data.terraform_remote_state.backup_persistent.outputs.s3_bucket_arn}/*"
    ]
  }

  statement {
    effect    = "Allow"
    actions   = ["autoscaling:UpdateAutoScalingGroup"]
    resources = [module.asg.asg_arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [data.terraform_remote_state.backup_persistent.outputs.sns_topic_arn]
  }
}

resource "aws_iam_role_policy" "backup_ec2_policy" {
  name   = "${local.env["name"]}-syncthing-backup"
  role   = module.ec2_role.iam_role_name
  policy = data.aws_iam_policy_document.backup_ec2_policy.json
}

resource "aws_ssm_parameter" "ebs_volume_id" {
  name  = "/${local.env["name"]}/backup/syncthing_ebs_volume_id"
  type  = "String"
  value = data.terraform_remote_state.backup_persistent.outputs.ebs_volume_id
}

resource "aws_ssm_parameter" "backup_s3_bucket" {
  name  = "/${local.env["name"]}/backup/backup_s3_bucket"
  type  = "String"
  value = data.terraform_remote_state.backup_persistent.outputs.s3_bucket_id
}

resource "aws_ssm_parameter" "backup_sns_topic_arn" {
  name  = "/${local.env["name"]}/backup/backup_sns_topic_arn"
  type  = "String"
  value = data.terraform_remote_state.backup_persistent.outputs.sns_topic_arn
}

resource "aws_ssm_parameter" "scale_down_after_backup" {
  name  = "/${local.env["name"]}/backup/scale_down_after_backup"
  type  = "String"
  value = "1"
}
