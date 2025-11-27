resource "kubernetes_service_v1" "speedtest_http" {
  metadata {
    namespace = module.namespace.name
    name      = "speedtest-http"
  }

  spec {
    type = "ClusterIP"

    selector = {
      "local/speedtest-service" = "true"
    }

    port {
      port = local.http_port
    }
  }
}

resource "kubernetes_deployment_v1" "speedtest" {
  metadata {
    namespace = module.namespace.name
    name      = "speedtest"
  }

  spec {
    replicas = 1

    strategy {
      type = "Recreate"
    }

    selector {
      match_labels = {
        "local/speedtest-service" = "true"
      }
    }

    template {
      metadata {
        name      = "speedtest"
        namespace = module.namespace.name
        labels = {
          "local/speedtest-service" = "true"
        }
      }

      spec {
        container {
          name  = "speedtest"
          image = var.image

          image_pull_policy = "IfNotPresent"
        }
      }
    }
  }
}

# Required so that Traefik does not reject large uploads, which
# causes OpenSpeedTest to report insanely high upload speeds.
resource "kubernetes_manifest" "buffering" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "Middleware"

    metadata = {
      namespace = module.namespace.name
      name      = "buffering"
    }

    spec = {
      buffering = {
        maxRequestBodyBytes = 52428800
        memRequestBodyBytes = 104857600
      }
    }
  }
}

resource "kubernetes_manifest" "ingress" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "IngressRoute"

    metadata = {
      namespace = module.namespace.name
      name      = "speedtest"
    }

    spec = {
      routes = [
        {
          match = "Host(`speedtest.${var.homelab_shared01_zone.host}`)"
          kind  = "Rule"
          services = [
            {
              name = kubernetes_service_v1.speedtest_http.metadata[0].name
              port = local.http_port
              kind = "Service"
            }
          ]
          middlewares = [
            {
              name = kubernetes_manifest.buffering.manifest.metadata.name
            },
          ]
        },
      ]
      tls = {
        certResolver = "gcp"
        domains = [{
          main = "speedtest.${var.homelab_shared01_zone.host}"
        }]
      }
    }
  }
}
