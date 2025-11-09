output "registry_ro_host" {
  description = "the hostname of the read-only registry host"
  value       = local.registry_ro_host
}

output "registry_ro_secret" {
  description = "secret containing information for read-only container registry access"
  value = {
    namespace = kubernetes_secret_v1.registry_ro.metadata[0].namespace
    name      = kubernetes_secret_v1.registry_ro.metadata[0].name
  }
}

output "registry_rw_host" {
  description = "the hostname of the read-write registry host"
  value       = local.registry_rw_host
}

output "registry_rw_secret" {
  description = "secret containing information for read-only container registry access"
  value = {
    namespace = kubernetes_secret_v1.registry_rw.metadata[0].namespace
    name      = kubernetes_secret_v1.registry_rw.metadata[0].name
  }
}
