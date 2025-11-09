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
