data "aws_route53_zone" "cert_zone" {
  name = data.terraform_remote_state.wedding_website_persistent.outputs.ssl_cert.domain_name
}

resource "aws_route53_record" "cert_validation" {
  count = length(local.ssl_cert.domain_validation_options)

  zone_id = data.aws_route53_zone.cert_zone.zone_id
  name    = local.ssl_cert.domain_validation_options[count.index].resource_record_name
  type    = local.ssl_cert.domain_validation_options[count.index].resource_record_type
  records = [local.ssl_cert.domain_validation_options[count.index].resource_record_value]
  ttl     = 30
}

resource "aws_acm_certificate_validation" "cert_validation" {
  certificate_arn         = local.ssl_cert.arn
  validation_record_fqdns = aws_route53_record.cert_validation.*.fqdn
}
