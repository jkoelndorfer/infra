output "file_transfer_url" {
  description = "base domain of S3 bucket that contains files for transfer"
  value       = "https://${aws_s3_bucket.file_transfer.bucket}.s3.amazonaws.com/"
}
