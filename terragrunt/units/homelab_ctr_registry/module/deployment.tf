locals {
  deployment_match_labels = {
    "local/registry-service" = "true"
  }
}

resource "kubernetes_service_v1" "registry" {
  metadata {
    namespace = module.namespace.name
    name      = "registry"
  }

  spec {
    type = "ClusterIP"

    selector = {
      "local/registry-service" = "true"
    }

    port {
      port = local.registry_port
    }
  }
}

resource "kubernetes_deployment_v1" "registry" {
  metadata {
    namespace = module.namespace.name
    name      = "registry"
  }

  spec {
    replicas = 1

    selector {
      match_labels = local.deployment_match_labels
    }

    template {
      metadata {
        namespace = module.namespace.name
        name      = "registry"
        labels    = local.deployment_match_labels
      }

      spec {
        container {
          name  = "registry"
          image = var.registry_image

          image_pull_policy = "IfNotPresent"

          security_context {
            run_as_user  = module.uid_gid.uid
            run_as_group = module.uid_gid.gid
          }

          port {
            container_port = local.registry_port
          }

          volume_mount {
            # See https://distribution.github.io/distribution/about/deploying/#customize-the-storage-location
            name       = "data"
            mount_path = "/var/lib/registry"
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

  depends_on = [
    module.data_volume,
  ]
}
