module "traefik_only_ingress" {
  source = "${var.paths.modules_root}/traefik_only_ingress_policy"

  namespace = module.namespace.name
}

resource "kubernetes_manifest" "argo_workflows_ingress" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "IngressRoute"

    metadata = {
      namespace = module.namespace.name
      name      = "argo-workflows"
    }

    spec = {
      routes = [
        {
          match = "Host(`argo-workflows.${var.homelab_shared01_zone.host}`)"
          kind  = "Rule"
          services = [
            {
              name = "argo-workflows-server"
              port = var.server_service_port_name
              kind = "Service"
            }
          ]
          middlewares = [
            {
              namespace = kubernetes_manifest.argo_workflows_server_auth.manifest["metadata"]["namespace"],
              name      = kubernetes_manifest.argo_workflows_server_auth.manifest["metadata"]["name"],
            },
          ]
        },
      ]
      tls = {
        certResolver = "gcp"
        domains = [{
          main = "argo-workflows.${var.homelab_shared01_zone.host}"
        }]
      }
    }
  }
}
