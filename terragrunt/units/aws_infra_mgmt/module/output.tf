output "infrastate-bucket" {
  description = "the bucket that infrastructure state files are kept in"
  value       = {
    arn    = aws_s3_bucket.infrastate.arn
    bucket = aws_s3_bucket.infrastate.bucket
  }
}
