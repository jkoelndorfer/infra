data "aws_route53_zone" "blog_zone" {
  name = "${local.env["dns_zone"]}."
}

resource "aws_route53_record" "blog" {
  zone_id = data.aws_route53_zone.blog_zone.zone_id
  name    = data.aws_route53_zone.blog_zone.name
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.blog.domain_name
    zone_id                = aws_cloudfront_distribution.blog.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "blog_www" {
  zone_id = data.aws_route53_zone.blog_zone.zone_id
  name    = "www.${data.aws_route53_zone.blog_zone.name}"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.blog.domain_name
    zone_id                = aws_cloudfront_distribution.blog.hosted_zone_id
    evaluate_target_health = false
  }
}
