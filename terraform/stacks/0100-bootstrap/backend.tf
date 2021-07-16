provider "aws" {
  region = local.env["default_aws_region"]
  # Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in the environment
}
