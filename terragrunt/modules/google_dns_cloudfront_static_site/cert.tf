resource "aws_acm_certificate" "this" {
  domain_name       = var.domain
  validation_method = "DNS"

  subject_alternative_names = ["www.${var.domain}"]

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_dns_record_set" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.this.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  managed_zone = data.google_managed_dns_zone.site_zone.name

  name = each.value.name
  type = each.value.type
  ttl  = 300

  rrdatas = ["\"${each.value.record}\""]
}

resource "aws_acm_certificate_validation" "this" {
  certificate_arn         = aws_acm_certificate.this.arn
  validation_record_fqdns = [for record in google_dns_record_set.cert_validation : record.name]
}
