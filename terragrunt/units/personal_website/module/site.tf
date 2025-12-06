module "site" {
  source = "${var.paths.modules_root}/google_dns_cloudfront_static_site"

  dns_name  = var.personal_zone.dns_name
  project   = var.dns_project.project_id
  zone_name = var.personal_zone.name
}
