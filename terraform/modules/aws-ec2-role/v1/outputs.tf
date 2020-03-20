output "iam_role_name" {
  value       = aws_iam_role.role.name
  description = "The name of the created IAM role (attach additional policies to this)"
}

output "iam_instance_profile_name" {
  value       = aws_iam_instance_profile.instance_profile.name
  description = "The name of the created IAM instance profile (used by the autoscaling group)"
}
