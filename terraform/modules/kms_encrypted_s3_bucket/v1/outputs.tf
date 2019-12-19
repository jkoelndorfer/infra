output "id" {
  value       = aws_s3_bucket.bucket.id
  description = "the name of the S3 bucket"
}

output "arn" {
  value       = aws_s3_bucket.bucket.arn
  description = "the ARN of the S3 bucket"
}
