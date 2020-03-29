data "aws_iam_policy_document" "dyndns_assume_role" {
  statement {
    sid     = "AllowLambdaServiceAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dyndns" {
  name = "${local.env["name"]}-lambda-dyndns"

  assume_role_policy = data.aws_iam_policy_document.dyndns_assume_role.json
}

data "aws_iam_policy_document" "lambda_dyndns" {
  statement {
    sid    = "AllowLambdaEC2Read"
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
      "ec2:DescribeTags",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaRoute53ReadWrite"
    effect = "Allow"
    actions = [
      "route53:ListHostedZones",
      "route53:ChangeResourceRecordSets",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "dyndns" {
  name        = "${local.env["name"]}-lambda-dyndns"
  description = "Policy permitting Lambda to perform actions needed for cloud dynamic DNS"
  policy      = data.aws_iam_policy_document.lambda_dyndns.json
}

resource "aws_iam_role_policy_attachment" "dyndns" {
  role       = aws_iam_role.dyndns.name
  policy_arn = aws_iam_policy.dyndns.arn
}

resource "aws_iam_role_policy_attachment" "dyndns_logging" {
  role       = aws_iam_role.dyndns.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

# TODO: Create a Lambda module that automatically handles logging
# and necessary permissions.

resource "random_string" "dyndns_pw" {
  length  = 64
  special = false
}

locals {
  dyndns_hostname = "home.${local.env["dns_zone"]}"
}

resource "aws_lambda_function" "dyndns" {
  # This is a dummy package so we can deploy the Lambda function.
  # Apply updates from the "infra" repository.
  filename      = "dyndns.zip"
  function_name = "${local.env["name"]}-dyndns"
  handler       = "dyndns.lambda_handler"
  role          = aws_iam_role.dyndns.arn
  description   = "Provides dynamic DNS for EC2 instances and authenticated clients."
  memory_size   = 128
  runtime       = "python3.7"
  timeout       = 5
  environment {
    variables = {
      "DYNDNS_AUTHORIZATION" = jsonencode({
        home = {
          password  = random_string.dyndns_pw.result
          dns_names = [local.dyndns_hostname]
        }
      })
      "env_name"             = local.env["name"]
    }
  }
  tags = {
    "johnk:category" = "core"
    "johnk:env"      = local.env["name"]
  }
}

resource "aws_ssm_parameter" "api_gateway_dyndns_username_home" {
  name        = "/${local.env["name"]}/dyndns/creds/home/username"
  type        = "String"
  value       = "home"
  description = "Username for home dynamic DNS in ${local.env["name"]}."
}

resource "aws_ssm_parameter" "api_gateway_dyndns_password_home" {
  name        = "/${local.env["name"]}/dyndns/creds/home/password"
  type        = "SecureString"
  value       = random_string.dyndns_pw.result
  description = "Password for home dynamic DNS in ${local.env["name"]}."
}

resource "aws_ssm_parameter" "api_gateway_dyndns_hostname" {
  name        = "/${local.env["name"]}/dyndns/hostname"
  type        = "String"
  value       = local.dyndns_hostname
  description = "Hostname for home dynamic DNS in ${local.env["name"]}."
}
