# NOTE: This stack depends on AWS WorkMail, for which there is not a Terraform resource.
data "aws_route53_zone" "email_domain" {
  name         = local.env.dns_zone
  private_zone = false
}

resource "aws_route53_record" "ownership_verification_and_spf" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = local.env.dns_zone
  type    = "TXT"
  ttl     = local.env.default_dns_ttl
  records = [local.env.ownership_verification, local.env.spf_record]
}

resource "aws_route53_record" "dmarc_record" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "_dmarc.${local.env.dns_zone}"
  type    = "TXT"
  ttl     = local.env.default_dns_ttl
  records = [local.env.dmarc_record]
}

resource "aws_route53_record" "mx" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = local.env.dns_zone
  type    = "MX"
  ttl     = local.env.default_dns_ttl
  records = local.env.mx_records
}

resource "aws_route53_record" "mail_mx" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "mail.${local.env.dns_zone}"
  type    = "MX"
  ttl     = local.env.default_dns_ttl
  records = local.env.mx_records
}

resource "aws_route53_record" "mail_spf" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "mail.${local.env.dns_zone}"
  type    = "TXT"
  ttl     = local.env.default_dns_ttl
  records = [local.env.spf_record]
}

resource "aws_route53_record" "dkim" {
  for_each = local.env.dkim_records

  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "${each.key}._domainkey.${local.env.dns_zone}."
  type    = "CNAME"
  ttl     = local.env.default_dns_ttl
  records = [each.value]
}
