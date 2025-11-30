resource "kubernetes_deployment_v1" "blocky" {
  metadata {
    namespace = module.namespace.name
    name      = "blocky"
  }

  spec {
    replicas = 1

    strategy {
      type = "Recreate"
    }

    selector {
      match_labels = {
        "local/blocky-service" = "true"
      }
    }

    template {
      metadata {
        name      = "blocky"
        namespace = module.namespace.name
        labels = {
          "local/blocky-service" = "true"
        }
      }

      spec {
        container {
          name  = "blocky"
          image = var.image

          image_pull_policy = "IfNotPresent"

          env {
            name  = "BLOCKY_CONFIG_FILE"
            value = "/config/main.yml"
          }

          security_context {
            run_as_user  = module.uid_gid.uid
            run_as_group = module.uid_gid.gid
          }

          port {
            protocol       = "UDP"
            container_port = local.container_dns_port
            host_port      = local.dns_port
          }

          volume_mount {
            name       = "config"
            mount_path = "/config"
          }
        }

        volume {
          name = "config"

          config_map {
            name         = "blocky"
            default_mode = "0444"
            items {
              key  = "main"
              path = "main.yml"
            }
          }
        }
      }
    }
  }
}

