data "aws_caller_identity" "current" {}

resource "aws_iam_role" "role" {
  name = "${var.env}-${var.name}"
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
  name = "${var.env}-${var.name}"
  role = aws_iam_role.role.name
}

resource "aws_iam_role_policy_attachment" "default_policy_attachment" {
  role       = aws_iam_role.role.name
  policy_arn = data.terraform_remote_state.core.outputs.ec2_default_policy_arn
}
