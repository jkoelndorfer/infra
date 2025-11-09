variable "aws_infra_mgmt_account" {
  description = "account used to support infrastructure management in AWS"
  type = object({
    arn   = string
    email = string
    env   = string
    id    = string

    organization_access_role = object({
      arn  = string
      name = string
    })
  })
}

variable "infrastate_s3_bucket" {
  description = "the infrastructure state S3 bucket"
  type        = object({ bucket = string })
}

variable "terragrunt_user" {
  description = "IAM user used to manage AWS organization via Terragrunt"
  type        = object({ arn = string, id = string, name = string })
}
