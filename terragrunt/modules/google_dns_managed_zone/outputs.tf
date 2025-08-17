locals {
  output_zone = local.create_zone ? google_dns_managed_zone.this[0] : data.google_dns_managed_zone.prod_dns_zone[0]
}

output "zone_was_created" {
  description = "true if a zone was created; false otherwise"
  value       = local.create_zone
}

output "name" {
  description = "the name of the zone; must be unique within a project"
  value       = local.output_zone.name
}

output "dns_name" {
  description = "the DNS name of the zone; e.g. 'example.com'"
  value       = local.zone_dns
}

output "email_domain" {
  description = "the part used after the '@' in emails addressed to this domain"
  value       = trimsuffix(local.zone_dns, ".")
}

output "host" {
  description = "the trailing part suffix for hosts in this zone"
  value       = trimsuffix(local.zone_dns, ".")
}

output "name_servers" {
  description = "name servers for the zone"
  value       = local.output_zone.name_servers
}

output "project" {
  description = "the project ID of the project containing the zone"
  value       = local.output_zone.project
}
