output "s3_bucket" {
  value = {
    for k, v in module.s3_bucket.bucket :
    k => v if contains(["arn", "bucket"], k)
  }
  description = "S3 bucket containing backups"
}

output "sns_topic" {
  value = {
    for k, v in aws_sns_topic.backup_notifications :
    k => v if contains(["arn", "name"], k)
  }
  description = "the SNS topic that backup notifications should be sent to"
}
