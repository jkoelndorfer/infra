# NOTE: We need to massage TXT records so they aren't improperly
# split before submitting them to Google Cloud DNS.
#
# See: https://registry.terraform.io/providers/hashicorp/google/6.46.0/docs/resources/dns_record_set#rrdatas-7

locals {
  google_spf_rrdata = ["v=spf1 include:_spf.google.com ~all"]
  google_mx_rrdata  = "1 smtp.google.com."
}

resource "google_dns_record_set" "dkim" {
  project = var.zone.project

  name         = "google._domainkey.${var.zone.dns_name}"
  managed_zone = var.zone.name
  type         = "TXT"
  ttl          = 300
  rrdatas      = ["\"${var.dkim_rrdata}\""]
}

resource "google_dns_record_set" "dmarc" {
  project = var.zone.project

  name         = "_dmarc.${var.zone.dns_name}"
  managed_zone = var.zone.name
  type         = "TXT"
  ttl          = 300
  rrdatas      = ["\"${var.dmarc_rrdata}\""]
}

resource "google_dns_record_set" "spf" {
  project = var.zone.project

  name         = var.zone.dns_name
  managed_zone = var.zone.name
  type         = "TXT"
  ttl          = 300
  rrdatas      = [for d in concat(var.addl_apex_txt_rrdata, local.google_spf_rrdata): "\"${d}\""]
}

resource "google_dns_record_set" "smtp" {
  project = var.zone.project

  name         = var.zone.dns_name
  managed_zone = var.zone.name
  type         = "MX"
  ttl          = 300
  rrdatas      = [local.google_mx_rrdata]
}
