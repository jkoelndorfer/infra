locals {
  create_zone = var.env == "prod" || var.enable_dev_zone ? true : false

  zone_dns_by_env = {
    dev  = "dev.${var.dns_name}"
    prod = var.dns_name
  }

  zone_dns  = "${local.zone_dns_by_env[var.env]}."
  zone_name = replace(replace(local.zone_dns, ".", "-"), "/-+$/", "")
}

resource "google_dns_managed_zone" "this" {
  count = local.create_zone ? 1 : 0

  project = var.project.project_id

  name        = local.zone_name
  dns_name    = local.zone_dns
  description = "${var.description} (${var.env})"

  labels = {
    function = var.function
  }
}
