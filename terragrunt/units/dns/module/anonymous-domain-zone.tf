data "google_secret_manager_secret_version_access" "anonymous_domains" {
  project = var.gcp_infra_mgmt_project.project_id

  secret = "anonymous-domains"
}

locals {
  anonymous_domains      = jsondecode(data.google_secret_manager_secret_version_access.anonymous_domains.secret_data)
  anonymous_domains_keys = nonsensitive([for k, v in local.anonymous_domains : k if k != "//"])
}

module "anonymous_domain_zone" {
  source   = "${var.paths.modules_root}/google_dns_managed_zone"
  for_each = toset(local.anonymous_domains_keys)

  description     = nonsensitive("anonymous domain ${each.key}")
  dns_name        = nonsensitive(local.anonymous_domains[each.key])
  enable_dev_zone = false
  env             = var.env
  function        = each.key
  project         = module.project
}
