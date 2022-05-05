output "s3_bucket" {
  value = {
    for k, v in module.s3_bucket.bucket :
    k => v if contains(["arn", "bucket"], k)
  }
  description = "S3 bucket containing backups"
}

output "ebs_volume" {
  value = {
    for k, v in module.ebs_volume.ebs_volume :
    k => v if contains(["availability_zone", "arn", "id"], k)
  }
  description = "the EBS volume containing syncthing data"
}

output "sns_topic" {
  value = {
    for k, v in aws_sns_topic.backup_notifications :
    k => v if contains(["arn", "name"], k)
  }
  description = "the SNS topic that backup notifications should be sent to"
}
