output "notice" {
  description = "notice indicating that SMTP password must be set"
  value       = "NOTICE: Configure Kubernetes secret SMTP containing Sendgrid API key"
}

output "deployment" {
  description = "the deployment that runs the vaultwarden service"
  value = {
    namespace = kubernetes_deployment_v1.vaultwarden.metadata[0].namespace
    name      = kubernetes_deployment_v1.vaultwarden.metadata[0].name
  }
}

output "data_volume" {
  description = "the volume containing vaultwarden data"
  value       = module.data_volume
}
