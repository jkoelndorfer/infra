locals {
  dev_zone_name = replace(local.zone_dns_by_env["dev"], ".", "-")
  delegate_dev  = var.env == "prod" && var.enable_dev_zone
}

data "google_projects" "dev_dns_project" {
  count = local.delegate_dev ? 1 : 0

  filter = "labels.env=dev labels.function=${var.project.labels.function}"
}

data "google_dns_managed_zone" "dev_dns_zone" {
  count = local.delegate_dev ? 1 : 0

  project = data.google_projects.dev_dns_project[0].projects[0].project_id
  name    = local.zone_name_by_env["dev"]
}

resource "google_dns_record_set" "dev_delegation" {
  count = local.delegate_dev ? 1 : 0

  project      = var.project.project_id
  managed_zone = google_dns_managed_zone.this[0].name
  name         = "${local.zone_dns_by_env["dev"]}."
  type         = "NS"
  rrdatas      = data.google_dns_managed_zone.dev_dns_zone[0].name_servers
}
