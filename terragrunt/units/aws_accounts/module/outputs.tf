output "aws_accounts" {
  description = "AWS accounts created by this unit"
  value       = { for k, v in local.accounts: k => module.aws_account[k] }
}
