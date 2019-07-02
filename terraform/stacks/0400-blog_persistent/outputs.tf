output "s3_bucket" {
  description = "s3 bucket that hosts the blog"
  value       = "${aws_s3_bucket.blog_bucket}"
}

output "ssl_cert" {
  description = "AWS ACM certificate that provides SSL for the blog"
  value       = "${aws_acm_certificate.blog}"
}
