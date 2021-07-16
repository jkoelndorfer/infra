output "arn" {
  value       = aws_ebs_volume.ebs_volume.arn
  description = "the ARN of the EBS volume"
}

output "availability_zone" {
  value       = aws_ebs_volume.ebs_volume.availability_zone
  description = "the ARN of the EBS volume"
}

output "id" {
  value       = aws_ebs_volume.ebs_volume.id
  description = "the ID of the EBS volume"
}
