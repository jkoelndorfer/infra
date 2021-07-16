output "s3_bucket" {
  description = "s3 bucket that hosts the blog"
  value       = {
    arn                         = aws_s3_bucket.blog_bucket.arn
    bucket                      = aws_s3_bucket.blog_bucket.bucket
    bucket_regional_domain_name = aws_s3_bucket.blog_bucket.bucket_regional_domain_name
  }
}

output "ssl_cert" {
  description = "AWS ACM certificate that provides SSL for the blog"
  value       = {
    arn                       = aws_acm_certificate.blog.arn
    domain_name               = aws_acm_certificate.blog.domain_name
    domain_validation_options = tolist(aws_acm_certificate.blog.domain_validation_options)
  }
}
