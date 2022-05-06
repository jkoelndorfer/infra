resource "aws_route53_record" "file_transfer" {
  zone_id = data.aws_route53_zone.zone.id
  name    = local.domain_name
  type    = "A"

  alias {
    name    = aws_cloudfront_distribution.file_transfer.domain_name
    zone_id = aws_cloudfront_distribution.file_transfer.hosted_zone_id

    evaluate_target_health = true
  }
}
