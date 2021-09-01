data "aws_route53_zone" "this_zone" {
  name = "${local.env.dns_zone}."
}

resource "aws_route53_record" "this" {
  zone_id = data.aws_route53_zone.this_zone.zone_id
  name    = data.aws_route53_zone.this_zone.name
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "this_www" {
  zone_id = data.aws_route53_zone.this_zone.zone_id
  name    = "www.${data.aws_route53_zone.this_zone.name}"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}
