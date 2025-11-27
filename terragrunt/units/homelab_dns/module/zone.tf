module "anonymous_domains" {
  source = "${var.paths.modules_root}/anonymous_domains"
}

module "homelab_shared01_zone" {
  source = "${var.paths.modules_root}/google_dns_managed_zone"

  description     = "homelab services"
  dns_name        = "in.${module.anonymous_domains.domains["shared01"]}"
  enable_dev_zone = false
  env             = var.env
  function        = "homelab"
  project         = module.project
}

resource "google_dns_record_set" "homelab_shared01_apex_txt" {
  project = module.project.project_id

  name = module.homelab_shared01_zone.dns_name
  type = "TXT"
  ttl  = 300

  managed_zone = module.homelab_shared01_zone.name

  rrdatas = [
    "\"${data.dns_txt_record_set.smtp2go_spf.record}\"",
  ]
}

resource "google_dns_record_set" "homelab_shared01_dmarc" {
  project = module.project.project_id

  name = "_dmarc.${module.homelab_shared01_zone.dns_name}"
  type = "TXT"
  ttl  = 300

  managed_zone = module.homelab_shared01_zone.name

  rrdatas = [
    "\"v=DMARC1;p=reject;rua=mailto:dmarc@${module.homelab_shared01_zone.host};pct=100;fo=1\"",
  ]
}
