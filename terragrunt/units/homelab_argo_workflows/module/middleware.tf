resource "random_string" "argo_workflows_server_password" {
  length  = 32
  lower   = true
  upper   = true
  numeric = true
  special = false
}

resource "kubernetes_secret_v1" "argo_workflows_server" {
  metadata {
    namespace = module.namespace.name
    name      = "argo-workflows-server"
  }

  type = "kubernetes.io/basic-auth"

  data = {
    username = "argo-workflows"
    password = random_string.argo_workflows_server_password.result
  }
}

resource "kubernetes_manifest" "argo_workflows_server_auth" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "Middleware"

    metadata = {
      namespace = module.namespace.name
      name      = "argo-workflows-server"
    }

    spec = {
      basicAuth = {
        secret = kubernetes_secret_v1.argo_workflows_server.metadata[0].name
      }
    }
  }

  depends_on = [
    kubernetes_secret_v1.argo_workflows_server,
  ]
}
