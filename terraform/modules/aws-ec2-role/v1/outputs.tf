output "iam_role" {
  value       = aws_iam_role.role
  description = "the created IAM role (attach additional policies to this)"
}

output "iam_instance_profile" {
  value       = aws_iam_instance_profile.instance_profile
  description = "the created IAM instance profile (used by the autoscaling group)"
}
