locals {
  name_env = "${var.name}-${var.env}"
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "role" {
  name = local.name_env
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_instance_profile" "instance_profile" {
  name = local.name_env
  role = aws_iam_role.role.name
}

resource "aws_iam_role_policy_attachment" "default_policy_attachment" {
  role       = aws_iam_role.role.name
  policy_arn = data.terraform_remote_state.core.outputs.ec2_default_policy.arn
}
