output "asg" {
  description = "the created autoscaling group"
  value       = aws_autoscaling_group.autoscaling_group
}
