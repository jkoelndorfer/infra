output "s3_bucket" {
  description = "s3 bucket that hosts the website"
  value = {
    for k, v in aws_s3_bucket.website_bucket:
      k => v if contains(["arn", "bucket", "bucket_regional_domain_name"], k)
  }
}

output "ssl_cert" {
  description = "AWS ACM certificate that provides SSL for the website"
  value = {
    arn                       = aws_acm_certificate.website.arn
    domain_name               = aws_acm_certificate.website.domain_name
    domain_validation_options = tolist(aws_acm_certificate.website.domain_validation_options)
  }
}
