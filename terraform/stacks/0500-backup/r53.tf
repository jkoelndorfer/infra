data "aws_route53_zone" "miniserv_zone" {
  name = "${local.env["dns_zone"]}."
}

resource "aws_route53_record" "miniserv" {
  zone_id = data.aws_route53_zone.miniserv_zone.id
  name    = "miniserv.${data.aws_route53_zone.miniserv_zone.name}"
  type    = "CNAME"
  records = ["home.johnk.io"]
  ttl     = 60
}
