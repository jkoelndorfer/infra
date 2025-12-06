output "johnk_io_zone" {
  description = "DNS zone for johnk.io"
  value       = module.johnk_io_zone
}

output "dns_project" {
  description = "the GCP project containing DNS zones"
  value       = module.project
}

output "org_primary_zone" {
  description = "DNS zone for the organization primary domain"
  value       = module.org_primary_zone
}

output "shared01_zone" {
  description = "DNS zone for the anonymous shared01 zone"
  value       = module.anonymous_domain_zone["shared01"]
}
