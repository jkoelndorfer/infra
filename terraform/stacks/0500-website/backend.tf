provider "aws" {
  region = local.env.default_aws_region
  # Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in the environment
}

terraform {
  backend "s3" {
    bucket               = "310987624463-tfstate-prod"
    key                  = "website.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}
