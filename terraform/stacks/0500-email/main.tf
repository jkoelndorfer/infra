# NOTE: This stack depends on AWS WorkMail, for which there is not a Terraform resource.
data "aws_route53_zone" "email_domain" {
  name         = local.env.dns_zone
  private_zone = false
}

resource "aws_ses_domain_identity" "email_domain" {
  domain = local.env.dns_zone
}

resource "aws_ses_domain_mail_from" "email_mail_from" {
  domain           = aws_ses_domain_identity.email_domain.domain
  mail_from_domain = "mail.${aws_ses_domain_identity.email_domain.domain}"
}

resource "aws_ses_domain_dkim" "email_dkim" {
  domain = aws_ses_domain_identity.email_domain.domain
}

resource "aws_route53_record" "ses_verification" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "_amazonses.${local.env.dns_zone}"
  type    = "TXT"
  ttl     = local.env.default_dns_ttl
  records = [aws_ses_domain_identity.email_domain.verification_token]
}

resource "aws_ses_domain_identity_verification" "email_domain" {
  domain = aws_ses_domain_identity.email_domain.id

  depends_on = [aws_route53_record.ses_verification]
}

resource "aws_route53_record" "spf" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = local.env.dns_zone
  type    = "TXT"
  ttl     = local.env.default_dns_ttl
  records = [local.env.spf_record]
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
  records = ["10 inbound-smtp.${local.env.aws_mail_region}.amazonaws.com."]
}

resource "aws_route53_record" "autodiscover" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "autodiscover.${local.env.dns_zone}"
  type    = "CNAME"
  ttl     = local.env.default_dns_ttl
  records = ["autodiscover.mail.${local.env.aws_mail_region}.awsapps.com."]
}

resource "aws_route53_record" "mail_mx" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "mail.${local.env.dns_zone}"
  type    = "MX"
  ttl     = local.env.default_dns_ttl
  records = ["10 feedback-smtp.${local.env.aws_mail_region}.amazonses.com."]
}

resource "aws_route53_record" "mail_spf" {
  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "mail.${local.env.dns_zone}"
  type    = "TXT"
  ttl     = local.env.default_dns_ttl
  records = [local.env.spf_record]
}

resource "aws_route53_record" "dkim" {
  count = 3

  zone_id = data.aws_route53_zone.email_domain.zone_id
  name    = "${element(aws_ses_domain_dkim.email_dkim.dkim_tokens, count.index)}._domainkey.${local.env.dns_zone}."
  type    = "CNAME"
  ttl     = local.env.default_dns_ttl
  records = ["${element(aws_ses_domain_dkim.email_dkim.dkim_tokens, count.index)}.dkim.amazonses.com."]
}
