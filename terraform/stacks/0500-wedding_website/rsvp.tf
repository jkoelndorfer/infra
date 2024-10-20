data "aws_iam_policy_document" "rsvp_assume_role" {
  statement {
    sid     = "AllowLambdaAssumeRole"
    effect  = "Allow"
    actions = [
      "sts:AssumeRole",
    ]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "rsvp" {
  statement {
    sid = "AllowDynamoAccess"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:WriteItem",
    ]

    resources = [
      data.terraform_remote_state.wedding_website_persistent.outputs.dynamodb_rsvp_table.arn,
    ]
  }
}

resource "aws_iam_policy" "rsvp" {
  name        = "wedding-rsvp-${local.env.name}"
  description = "Policy granting required access for the wedding RSVP system in ${local.env.name}."
  policy      = data.aws_iam_policy_document.rsvp.json
}

resource "aws_iam_role" "rsvp" {
  name = "wedding-rsvp-${local.env.name}"

  assume_role_policy = data.aws_iam_policy_document.rsvp_assume_role.json
}

resource "random_password" "rsvp_api_key" {
    length  = 64
    lower   = true
    upper   = true
    numeric = true
    special = false
}

data "archive_file" "rsvp_stub" {
  type = "zip"

  output_path = "rsvp.zip"

  source {
    content  = file("rsvpstub.py")
    filename = "rsvp.py"
  }
}

resource "aws_lambda_function" "rsvp" {
  # This is a dummy package so we can deploy the Lambda function.
  # Apply updates from the "infra" repository.
  filename      = data.archive_file.rsvp_stub.output_path
  function_name = "rsvp-${local.env.name}"
  handler       = "rsvp.lambda_handler"
  role          = aws_iam_role.rsvp.arn
  description   = "Provides RSVP capabilities for the Koelndorfer wedding website"
  memory_size   = 128
  runtime       = "python3.12"
  timeout       = 10

  environment {
    variables = {
      "API_KEY" = random_password.rsvp_api_key.result
    }
  }
}

locals {
  base_rsvp_cors_origins = [
    "https://${local.wedding_website_domain}",
    "https://${local.wedding_website_www_domain}",
  ]
  dev_rsvp_cors_origins = ["http://localhost:1313"]

  rsvp_cors_origins = local.env.name == "prod" ? local.base_rsvp_cors_origins : concat(local.base_rsvp_cors_origins, local.dev_rsvp_cors_origins)
}

resource "aws_lambda_function_url" "rsvp" {
  function_name      = aws_lambda_function.rsvp.function_name
  authorization_type = "NONE"

  cors {
    allow_methods = ["*"]
    allow_origins = local.rsvp_cors_origins
  }
}
