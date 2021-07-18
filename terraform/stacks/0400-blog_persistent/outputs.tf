output "s3_bucket" {
  description = "s3 bucket that hosts the blog"
  value = {
    for k, v in aws_s3_bucket.blog_bucket:
      k => v if contains(["arn", "bucket", "bucket_regional_domain_name"], k)
  }
}

output "ssl_cert" {
  description = "AWS ACM certificate that provides SSL for the blog"
  value = {
    arn                       = aws_acm_certificate.blog.arn
    domain_name               = aws_acm_certificate.blog.domain_name
    domain_validation_options = tolist(aws_acm_certificate.blog.domain_validation_options)
  }
}
