output "uid" {
  description = "the UID of the service in the given environment"
  value       = local.service_id
}

output "gid" {
  description = "the GID of the service in the given environment"
  value       = local.service_id
}
