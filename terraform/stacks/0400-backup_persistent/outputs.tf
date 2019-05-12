output "s3_bucket_arn" {
  value       = "${module.s3_bucket.arn}"
  description = "ARN of the S3 bucket containing backups"
}

output "s3_bucket_id" {
  value       = "${module.s3_bucket.id}"
  description = "ID of the S3 bucket containing backups"
}

output "ebs_volume_arn" {
  value       = "${module.ebs_volume.arn}"
  description = "ARN of the EBS volume containing syncthing data"
}

output "ebs_volume_az" {
  value       = "${module.ebs_volume.availability_zone}"
  description = "The AZ that the EBS volume is located in"
}

output "ebs_volume_id" {
  value       = "${module.ebs_volume.id}"
  description = "ID of the EBS volume containing syncthing data"
}

output "sns_topic_arn" {
  value       = "${aws_sns_topic.backup_notifications.arn}"
  description = "ARN of the SNS topic that backup notifications should be sent to"
}
