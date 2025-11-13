output "deployment" {
  description = "the deployment that runs the syncthing service"
  value = {
    namespace = kubernetes_deployment_v1.syncthing.metadata[0].namespace
    name      = kubernetes_deployment_v1.syncthing.metadata[0].name
  }
}

output "config_volume" {
  description = "the volume containing syncthing data"
  value       = module.config_volume
}

output "data_volume" {
  description = "the volume containing syncthing data"
  value       = module.data_volume
}
