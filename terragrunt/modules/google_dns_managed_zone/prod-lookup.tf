locals {
  lookup_prod = var.env == "dev" && !var.enable_dev_zone
}

data "google_projects" "prod_dns_project" {
  count = local.lookup_prod ? 1 : 0

  filter = "labels.env=prod labels.function=${var.project.labels.function}"
}

data "google_dns_managed_zone" "prod_dns_zone" {
  count = local.lookup_prod ? 1 : 0

  project = data.google_projects.prod_dns_project[0].projects[0].project_id
  name    = local.zone_name_by_env["prod"]
}
