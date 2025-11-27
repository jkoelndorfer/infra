resource "google_dns_record_set" "smtp2go_return" {
  project = module.project.project_id

  name = "em911349.${module.homelab_shared01_zone.dns_name}"
  type = "CNAME"
  ttl  = 300

  managed_zone = module.homelab_shared01_zone.name

  rrdatas = ["return.smtp2go.net."]
}

resource "google_dns_record_set" "smtp2go_dkim" {
  project = module.project.project_id

  name = "s911349._domainkey.${module.homelab_shared01_zone.dns_name}"
  type = "CNAME"
  ttl  = 300

  managed_zone = module.homelab_shared01_zone.name

  rrdatas = ["dkim.smtp2go.net."]
}

data "dns_txt_record_set" "smtp2go_spf" {
  host = "return.smtp2go.net"
}
