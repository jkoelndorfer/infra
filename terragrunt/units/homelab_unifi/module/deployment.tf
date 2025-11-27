locals {
  deployment_match_labels = {
    "local/unifi-service" = "true"
  }

  # See https://github.com/linuxserver-archive/docker-unifi-controller?tab=readme-ov-file#parameters
  stun_port         = 3478
  device_port       = 8080
  web_port          = 8443
  ap_discovery_port = 10001
}

resource "kubernetes_service_v1" "unifi_web" {
  metadata {
    namespace = module.namespace.name
    name      = "unifi-web"
  }

  spec {
    type = "ClusterIP"

    selector = local.deployment_match_labels

    port {
      # Causes Traefik to treat traffic to this service as HTTPS.
      # See https://doc.traefik.io/traefik/reference/routing-configuration/kubernetes/ingress/#communication-between-traefik-and-pods
      port = 443

      target_port = local.web_port
    }
  }
}

resource "kubernetes_deployment_v1" "unifi" {
  metadata {
    namespace = module.namespace.name
    name      = "unifi"
  }

  spec {
    replicas = 1

    selector {
      match_labels = local.deployment_match_labels
    }

    strategy {
      type = "Recreate"
    }

    template {
      metadata {
        namespace = module.namespace.name
        name      = "unifi"
        labels    = local.deployment_match_labels
      }

      spec {
        container {
          name  = "unifi"
          image = var.unifi_image

          image_pull_policy = "IfNotPresent"

          env {
            name  = "PUID"
            value = module.uid_gid.uid
          }

          env {
            name  = "PGID"
            value = module.uid_gid.gid
          }

          port {
            protocol       = "TCP"
            container_port = local.web_port
          }

          port {
            protocol       = "TCP"
            container_port = local.device_port
            host_port      = local.device_port
          }

          port {
            protocol       = "UDP"
            container_port = local.ap_discovery_port
            host_port      = local.ap_discovery_port
          }

          port {
            protocol       = "UDP"
            container_port = local.stun_port
            host_port      = local.stun_port
          }

          volume_mount {
            name       = "config"
            mount_path = "/config"
          }
        }

        volume {
          name = "config"
          persistent_volume_claim {
            claim_name = module.config_volume.pvc.name
          }
        }
      }
    }
  }

  depends_on = [
    module.config_volume,
  ]
}

resource "kubernetes_manifest" "insecure_transport" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "ServersTransport"

    metadata = {
      namespace = module.namespace.name
      name      = "insecure-transport"
    }

    spec = {
      insecureSkipVerify = true
    }
  }
}

resource "kubernetes_manifest" "unifi_ingress" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "IngressRoute"

    metadata = {
      namespace = module.namespace.name
      name      = "unifi"
    }

    spec = {
      routes = [
        {
          match = "Host(`unifi.${var.homelab_shared01_zone.host}`)"
          kind  = "Rule"
          services = [
            {
              name = kubernetes_service_v1.unifi_web.metadata[0].name
              port = 443
              kind = "Service"

              serversTransport = kubernetes_manifest.insecure_transport.manifest.metadata.name
            }
          ]
        },
      ]
      tls = {
        certResolver = "gcp"
        domains = [{
          main = "unifi.${var.homelab_shared01_zone.host}"
        }]
      }
    }
  }
}
