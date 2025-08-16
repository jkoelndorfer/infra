module "org_primary_zone" {
  source = "${var.paths.modules_root}/google_dns_managed_zone"

  description     = "organization primary zone"
  dns_name        = var.gcp_organization.domain
  enable_dev_zone = true
  env             = var.env
  function        = "org-primary"
  project         = module.project
}
