locals {
  output_zone = {
    name         = local.create_zone ? google_dns_managed_zone.this[0].name : "zone-was-not-created"
    dns_name     = local.create_zone ? google_dns_managed_zone.this[0].dns_name : local.zone_dns
    name_servers = local.create_zone ? google_dns_managed_zone.this[0].name_servers : []
    project      = local.create_zone ? google_dns_managed_zone.this[0].project : var.project.project_id
  }
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
  value       = local.output_zone.dns_name
}

output "email_domain" {
  description = "the part used after the '@' in emails addressed to this domain"
  value       = trimsuffix(local.output_zone.dns_name, ".")
}

output "name_servers" {
  description = "name servers for the zone"
  value       = local.output_zone.name_servers
}

output "project" {
  description = "the project ID of the project containing the zone"
  value       = local.output_zone.project
}
