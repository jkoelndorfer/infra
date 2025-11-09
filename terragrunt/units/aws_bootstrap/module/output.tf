output "aws_infra_mgmt_account" {
  description = "the AWS account used for infrastructure management"
  value       = module.infra_mgmt_account
}

output "terragrunt_user" {
  description = "IAM user used to manage AWS organization via Terragrunt"
  value       = {
    arn  = aws_iam_user.terragrunt.arn
    id   = aws_iam_user.terragrunt.id
    name = aws_iam_user.terragrunt.name
  }
}

output "notice" {
  description = "not a real value; used to inform user of required action"
  value       = "NOTICE: Create an IAM credential for ${aws_iam_user.terragrunt.arn} and add it to the AWS credential path (see root.hcl)"
}
