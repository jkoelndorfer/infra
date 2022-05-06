output "s3_bucket" {
  description = "S3 bucket that contains files for transfer"
  value = {
    bucket = aws_s3_bucket.file_transfer.bucket
  }
}

output "file_transfer_url" {
  description = "base domain of S3 bucket that contains files for transfer"
  value       = "https://${local.domain_name}"
}
