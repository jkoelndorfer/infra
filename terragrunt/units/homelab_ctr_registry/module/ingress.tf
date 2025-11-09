module "traefik_only_ingress" {
  source = "${var.paths.modules_root}/traefik_only_ingress_policy"

  namespace = module.namespace.name
}

resource "kubernetes_manifest" "registry_ingress" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "IngressRoute"

    metadata = {
      namespace = module.namespace.name
      name      = "registry"
    }

    spec = {
      routes = [
        {
          match    = "Host(`${local.registry_rw_host}`)"
          priority = 110
          kind     = "Rule"
          services = [
            {
              name = kubernetes_service_v1.registry.metadata[0].name
              port = local.registry_port
              kind = "Service"
            }
          ]
          middlewares = [
            {
              namespace = kubernetes_manifest.registry_middleware_rw.manifest["metadata"]["namespace"],
              name      = kubernetes_manifest.registry_middleware_rw.manifest["metadata"]["name"],
            },
          ]
        },
        {
          match    = "Host(`${local.registry_ro_host}`) && ( Method(`GET`) || METHOD(`HEAD`) || METHOD(`TRACE`) )"
          priority = 101
          kind     = "Rule"
          services = [
            {
              name = kubernetes_service_v1.registry.metadata[0].name
              port = local.registry_port
              kind = "Service"
            }
          ]
          middlewares = [
            {
              namespace = kubernetes_manifest.registry_middleware_ro.manifest["metadata"]["namespace"],
              name      = kubernetes_manifest.registry_middleware_ro.manifest["metadata"]["name"],
            },
          ]
        },
        {
          match    = "Host(`${local.registry_ro_host}`)"
          priority = 100
          kind     = "Rule"
          services = [
            {
              name = kubernetes_service_v1.registry.metadata[0].name
              port = local.registry_port
              kind = "Service"
            }
          ]
          middlewares = [
            {
              namespace = kubernetes_manifest.registry_middleware_dummy.manifest["metadata"]["namespace"],
              name      = kubernetes_manifest.registry_middleware_dummy.manifest["metadata"]["name"],
            },
          ]
        },
      ]
      tls = {
        certResolver = "gcp"
        domains = [{
          main = local.registry_rw_host
          sans = [
            local.registry_ro_host,
          ]
        }]
      }
    }
  }

  depends_on = [
    kubernetes_manifest.registry_middleware_ro,
    kubernetes_manifest.registry_middleware_rw,
  ]
}
