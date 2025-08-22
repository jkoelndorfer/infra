data "google_secret_manager_secret_version_access" "anonymous_domains" {
  project = var.google_infra_mgmt_project.project_id

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

module "shared01_email_records" {
  count  = module.anonymous_domain_zone["shared01"].zone_was_created ? 1 : 0
  source = "${var.paths.modules_root}/google_email_dns_records"

  addl_apex_txt_rrdata = [
    "google-site-verification=kP1nGF8YG_hBqmH12MRVUmS3EeeKgWcfup1gvuCgDZQ",
  ]
  dkim_rrdata  = "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCRcB59JQSci5idLN7cY57ejTUpVWNsjWqTy7LNhIKiePVGpBV9vwTn8n+JrKQk71d9PoXTf2cfNS1MKaZhqoWMiDCC6fzWFGiH2ySyyTYdUAmg4iDfaR+RVuh6oFJt/4zN3Lz6f8ADKDyLNO8Vlfmy2sljjQn5/BUXpqtiGiqYOwIDAQAB"
  dmarc_rrdata = "v=DMARC1;p=none;pct=100;fo=1;rua=mailto:dmarc@${module.anonymous_domain_zone["shared01"].email_domain}"
  zone         = module.anonymous_domain_zone["shared01"]
}

module "jk_shared01_email_records" {
  count  = module.anonymous_domain_zone["shared01"].zone_was_created ? 1 : 0
  source = "${var.paths.modules_root}/google_email_dns_records"

  addl_apex_txt_rrdata = []
  dkim_rrdata          = "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYj1MlzaWTXJUNR/xjwKxxLPVFGlK12GNKQc4N6oZFdWXGacIq0FxQHciCO1e14Zx56gM4M+SfKjLVSa0lwfa4MEaAPvaTGLiVUSMTstCPz3lXIr5sFiMqmPANilw24Bzfnn1KxdKb9jYHhWOnVXLMEFraJLb8VrkpBe7aA8lVFQIDAQAB"
  dmarc_rrdata         = "v=DMARC1;p=none;pct=100;fo=1;rua=mailto:dmarc@jk.${module.anonymous_domain_zone["shared01"].email_domain}"
  zone = merge(
    module.anonymous_domain_zone["shared01"],
    {
      dns_name = "jk.${module.anonymous_domain_zone["shared01"].dns_name}"
    }
  )
}
