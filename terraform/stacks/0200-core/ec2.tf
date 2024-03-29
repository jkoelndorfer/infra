resource "aws_key_pair" "default" {
  key_name   = "default-${local.env.name}"
  public_key = local.env.default_ec2_public_key
}

resource "aws_iam_policy" "ec2_default_policy" {
  name   = "ec2-default-${local.env.name}"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
              "ssm:GetParameter",
              "ssm:GetParameterByPath",
              "ssm:GetParameters"
            ],
            "Resource": "arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter/provision/common/*"
        }
    ]
}
EOF
}

resource "aws_iam_role" "role" {
  name               = "ec2-default-${local.env.name}"
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
  name = "ec2-default-${local.env.name}"
  role = aws_iam_role.role.name
}

resource "aws_iam_role_policy_attachment" "ec2_default_policy_attachment" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.ec2_default_policy.arn
}
