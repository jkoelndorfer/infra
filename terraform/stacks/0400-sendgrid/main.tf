data "aws_route53_zone" "zone" {
  name = local.env.zone
}

resource "aws_route53_record" "mx" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${local.env.records.mx.name}.${local.env.domain}"
  type    = "MX"
  ttl     = 300
  records = [local.env.records.mx.value]
}

resource "aws_route53_record" "spf" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${local.env.records.spf.name}.${local.env.domain}"
  type    = "TXT"
  ttl     = 300
  records = [local.env.records.spf.value]
}

resource "aws_route53_record" "dkim" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${local.env.records.dkim.name}.${local.env.domain}"
  type    = "TXT"
  ttl     = 300
  records = [local.env.records.dkim.value]
}
