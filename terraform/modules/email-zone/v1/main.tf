data "aws_route53_zone" "zone" {
  name         = var.zone
  private_zone = false
}

resource "aws_route53_record" "spf" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = var.zone
  type    = "TXT"
  ttl     = var.dns_ttl
  records = [var.spf_record]
}

resource "aws_route53_record" "dmarc_record" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "_dmarc.${var.zone}"
  type    = "TXT"
  ttl     = var.dns_ttl
  records = [var.dmarc_record]
}

resource "aws_route53_record" "mx" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = var.zone
  type    = "MX"
  ttl     = var.dns_ttl
  records = var.mx_records
}

resource "aws_route53_record" "dkim" {
  for_each = var.dkim_records

  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${each.key}._domainkey.${var.zone}."
  type    = "CNAME"
  ttl     = var.dns_ttl
  records = [each.value]
}
