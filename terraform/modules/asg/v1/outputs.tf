output "asg_arn" {
  description = "the ARN of the created autoscaling group"
  value       = "${aws_autoscaling_group.autoscaling_group.arn}"
}

output "asg_name" {
  description = "the name of the created autoscaling group"
  value       = "${aws_autoscaling_group.autoscaling_group.name}"
}
