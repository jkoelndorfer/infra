resource "kubernetes_service_v1" "syncthing_sync" {
  metadata {
    namespace = module.namespace.name
    name      = "syncthing-sync-protocol"
  }

  spec {
    type = "NodePort"

    selector = {
      "local/syncthing-service" = "true"
    }

    port {
      port = local.sync_protocol_port
    }
  }
}

resource "kubernetes_service_v1" "syncthing_web_ui" {
  metadata {
    namespace = module.namespace.name
    name      = "syncthing-web-ui"
  }

  spec {
    type = "ClusterIP"

    selector = {
      "local/syncthing-service" = "true"
    }

    port {
      port = local.web_ui_port
    }
  }
}

resource "kubernetes_service_v1" "syncthing" {
  metadata {
    namespace = module.namespace.name
    name      = "syncthing"
  }

  spec {
    # This is a headless service for discovery by the stateful set.
    # See:
    #   - https://kubernetes.io/docs/concepts/services-networking/service/#headless-services
    #   - https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#limitations
    type       = "ClusterIP"
    cluster_ip = "None"

    selector = {
      "local/syncthing-service" = "true"
    }
  }
}

resource "kubernetes_deployment_v1" "syncthing" {
  metadata {
    namespace = module.namespace.name
    name      = "syncthing"
  }

  spec {
    replicas = 1

    strategy {
      type = "Recreate"
    }

    selector {
      match_labels = {
        "local/syncthing-service" = "true"
      }
    }

    template {
      metadata {
        name      = "syncthing"
        namespace = module.namespace.name
        labels = {
          "local/syncthing-service" = "true"
        }
      }

      spec {
        container {
          name  = "syncthing"
          image = "linuxserver/syncthing:v2.0.9-ls196"

          image_pull_policy = "IfNotPresent"

          env {
            name  = "PUID"
            value = var.syncthing_uid
          }

          env {
            name  = "PGID"
            value = var.syncthing_gid
          }

          port {
            container_port = local.sync_protocol_port
            host_port      = local.sync_protocol_port
          }

          port {
            container_port = local.web_ui_port
          }

          volume_mount {
            name       = "config"
            mount_path = "/config"
          }

          volume_mount {
            name       = "data"
            mount_path = "/data"
          }
        }

        volume {
          name = "config"
          persistent_volume_claim {
            claim_name = module.config_volume.pvc.name
          }
        }

        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = module.data_volume.pvc.name
          }
        }
      }
    }
  }
}

resource "kubernetes_manifest" "syncthing_ingress" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "IngressRoute"

    metadata = {
      namespace = module.namespace.name
      name      = "syncthing"
    }

    spec = {
      routes = [
        {
          match = "Host(`syncthing.${var.homelab_shared01_zone.host}`)"
          kind  = "Rule"
          services = [
            {
              name = "syncthing-web-ui"
              port = local.web_ui_port
              kind = "Service"
            }
          ]
        },
      ]
      tls = {
        certResolver = "gcp"
        domains = [{
          main = "syncthing.${var.homelab_shared01_zone.host}"
        }]
      }
    }
  }
}
