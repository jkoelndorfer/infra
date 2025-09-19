resource "google_dns_record_set" "shared01_homelab_ns" {
  count   = module.anonymous_domain_zone["shared01"].zone_was_created ? 1 : 0
  project = module.project.project_id

  managed_zone = module.anonymous_domain_zone["shared01"].name
  name         = "in.${module.anonymous_domain_zone["shared01"].dns_name}"
  type         = "NS"
  ttl          = "600"
  rrdatas      = var.homelab_shared01_zone.name_servers
}
