resource "kubernetes_deployment_v1" "vaultwarden" {
  metadata {
    namespace = module.namespace.name
    name      = "vaultwarden"
  }

  spec {
    replicas = 1

    strategy {
      type = "Recreate"
    }

    selector {
      match_labels = {
        "local/vaultwarden-service" = "true"
      }
    }

    template {
      metadata {
        name      = "vaultwarden"
        namespace = module.namespace.name
        labels = {
          "local/vaultwarden-service" = "true"
        }
      }

      spec {
        container {
          name  = "vaultwarden"
          image = var.vaultwarden_image

          image_pull_policy = "IfNotPresent"

          security_context {
            run_as_user  = module.uid_gid.uid
            run_as_group = module.uid_gid.gid
          }

          env {
            name  = "DOMAIN"
            value = "https://vaultwarden.${var.homelab_shared01_zone.host}"
          }

          env {
            name  = "LOG_FILE"
            value = "${local.log_directory}/vaultwarden.log"
          }

          env {
            name  = "ROCKET_ADDRESS"
            value = "0.0.0.0"
          }

          env {
            name  = "ROCKET_PORT"
            value = local.web_ui_port
          }

          env {
            name  = "SHOW_PASSWORD_HINT"
            value = "false"
          }

          env {
            name  = "SIGNUPS_ALLOWED"
            value = "false"
          }

          env {
            name  = "WEBSOCKET_ENABLED"
            value = "true"
          }

          dynamic "env" {
            for_each = local.smtp

            content {
              name  = "SMTP_${upper(env.key)}"
              value = env.value
            }
          }

          env {
            name = "SMTP_USERNAME"
            value_from {
              secret_key_ref {
                name = "smtp"
                key  = "smtp2go_username"
              }
            }
          }

          env {
            name = "SMTP_PASSWORD"
            value_from {
              secret_key_ref {
                name = "smtp"
                key  = "smtp2go_password"
              }
            }
          }

          port {
            container_port = local.web_ui_port
          }

          volume_mount {
            name       = "data"
            mount_path = "/data"
          }

          volume_mount {
            name       = "log"
            mount_path = local.log_directory
          }
        }

        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = module.data_volume.pvc.name
          }
        }

        volume {
          name = "log"
          persistent_volume_claim {
            claim_name = module.log_volume.pvc.name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "vaultwarden_web_ui" {
  metadata {
    namespace = module.namespace.name
    name      = "vaultwarden-web-ui"
  }

  spec {
    type = "ClusterIP"

    selector = {
      "local/vaultwarden-service" = "true"
    }

    port {
      port = local.web_ui_port
    }
  }
}

resource "kubernetes_manifest" "vaultwarden_ingress" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "IngressRoute"

    metadata = {
      namespace = module.namespace.name
      name      = "vaultwarden"
    }

    spec = {
      routes = [
        {
          match = "Host(`vaultwarden.${var.homelab_shared01_zone.host}`)"
          kind  = "Rule"
          services = [
            {
              name = "vaultwarden-web-ui"
              port = local.web_ui_port
              kind = "Service"
            }
          ]
        },
      ]
      tls = {
        certResolver = "gcp"
        domains = [{
          main = "vaultwarden.${var.homelab_shared01_zone.host}"
        }]
      }
    }
  }
}
