output "s3_bucket" {
  description = "the S3 bucket backing the static site"
  value       = aws_s3_bucket.this
}

output "cloudfront_distribution" {
  description = "the CloudFront distribution hosting the static site"
  value       = aws_cloudfront_distribution.this
}
