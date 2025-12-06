resource "google_dns_record_set" "root" {

  managed_zone = data.google_managed_dns_zone.site_zone.name

  name = var.domain
  type = "CNAME"
  ttl  = 300

  rrdatas = ["\"${aws_cloudfront_distribution.this.domain_name}.\""]
}

resource "google_dns_record_set" "www" {

  managed_zone = data.google_managed_dns_zone.site_zone.name

  name = "www.${var.domain}"
  type = "CNAME"
  ttl  = 300

  rrdatas = ["\"${aws_cloudfront_distribution.this.domain_name}.\""]
}
