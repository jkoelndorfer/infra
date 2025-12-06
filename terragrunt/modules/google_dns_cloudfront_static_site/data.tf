locals {
  domain      = trimsuffix(var.dns_name, ".")
  domain_slug = replace(local.domain, ".", "-")
}

data "aws_caller_identity" "current" {}

data "google_dns_managed_zone" "site_zone" {
  project = var.project

  name = var.zone_name
}
