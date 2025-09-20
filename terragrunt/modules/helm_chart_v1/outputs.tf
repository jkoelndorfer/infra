output "kubernetes_manifest" {
  description = "the kubernetes manifest resource that defines the Helm chart"
  value       = kubernetes_manifest.this
}
