output "organization_access_role" {
  description = "the IAM role that can be assumed to access this AWS account"
  value = {
    name = aws_organizations_account.this.role_name
    arn  = "arn:aws:iam::${aws_organizations_account.this.id}:role/${aws_organizations_account.this.role_name}"
  }
}

output "arn" {
  description = "the AWS account ARN"
  value       = aws_organizations_account.this.arn
}

output "email" {
  description = "the AWS account owner email"
  value       = aws_organizations_account.this.email
}

output "env" {
  description = "the environment that the AWS account is deployed into"
  value       = var.env
}

output "id" {
  description = "the AWS account ID"
  value       = aws_organizations_account.this.id
}
