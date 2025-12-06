resource "google_dns_record_set" "root" {
  project = var.project

  managed_zone = data.google_dns_managed_zone.site_zone.name

  name = var.dns_name
  type = "CNAME"
  ttl  = 300

  rrdatas = ["${aws_cloudfront_distribution.this.domain_name}."]
}

resource "google_dns_record_set" "www" {
  project = var.project

  managed_zone = data.google_dns_managed_zone.site_zone.name

  name = "www.${var.dns_name}"
  type = "CNAME"
  ttl  = 300

  rrdatas = ["${aws_cloudfront_distribution.this.domain_name}."]
}
