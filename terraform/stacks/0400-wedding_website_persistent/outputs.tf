output "dynamodb_rsvp_table" {
  description = "DyanmoDB table used for wedding invites and response tracking"
  value       = {
    arn  = aws_dynamodb_table.wedding_invite.arn
    id   = aws_dynamodb_table.wedding_invite.id
    name = aws_dynamodb_table.wedding_invite.name
  }
}

output "s3_bucket" {
  description = "S3 bucket hosting website files"
  value       = {
    arn    = aws_s3_bucket.wedding_website_bucket.arn
    bucket = aws_s3_bucket.wedding_website_bucket.bucket

    bucket_regional_domain_name = aws_s3_bucket.wedding_website_bucket.bucket_regional_domain_name
  }
}

output "ssl_cert" {
  description = "AWS ACM certificate that provides SSL for the website"
  value       = {
    arn                       = aws_acm_certificate.wedding_website.arn
    domain_name               = aws_acm_certificate.wedding_website.domain_name
    domain_validation_options = tolist(aws_acm_certificate.wedding_website.domain_validation_options)
  }
}
