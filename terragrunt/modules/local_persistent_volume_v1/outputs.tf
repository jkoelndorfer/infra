output "access_modes" {
  description = "the volume's access modes"
  value       = var.access_modes
}

output "backing_volume" {
  description = "the name of the backing disk that the PersistentVolume resides on"
  value       = var.backing_volume
}

output "env" {
  description = "the environment that the volume is deployed in"
  value       = var.env
}

output "pv" {
  description = "the created persistent volume"
  value = {
    name = kubernetes_persistent_volume_v1.this.metadata[0].name
  }
}

output "pvc" {
  description = "the created persistent volume claim"
  value = {
    namespace = kubernetes_persistent_volume_claim_v1.this.metadata[0].namespace
    name      = kubernetes_persistent_volume_claim_v1.this.metadata[0].name
  }
}

output "storage" {
  description = "the requested storage capacity of the volume"
  value       = var.storage
}

output "volume_reclaim_policy" {
  description = "the kubernetes volume reclaim policy"
  value       = var.volume_reclaim_policy
}
