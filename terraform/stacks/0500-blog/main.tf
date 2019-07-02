data "aws_route53_zone" "blog_zone" {
  name = "${local.env["dns_zone"]}."
}

resource "aws_route53_record" "blog" {
  zone_id = data.aws_route53_zone.blog_zone.zone_id
  name    = "${data.aws_route53_zone.blog_zone.name}"
  type    = "A"
  alias {
    name                   = data.terraform_remote_state.blog_persistent.outputs.s3_bucket.website_domain
    zone_id                = data.terraform_remote_state.blog_persistent.outputs.s3_bucket.hosted_zone_id
    evaluate_target_health = false
  }
}
