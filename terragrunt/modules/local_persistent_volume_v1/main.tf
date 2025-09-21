locals {
  # This is the storage class that ships with k3s to
  # configure local directories.
  #
  # See https://docs.k3s.io/storage
  storage_class = "local-path"

  pv_attrs = var.directory_override != null ? var.directory_override : { namespace = var.namespace, name = var.name }
}

resource "kubernetes_persistent_volume_v1" "this" {
  metadata {
    name = var.name
  }

  spec {
    capacity = {
      storage = var.storage
    }
    access_modes = var.access_modes
    volume_mode  = "Filesystem"

    storage_class_name = local.storage_class

    persistent_volume_reclaim_policy = var.volume_reclaim_policy

    persistent_volume_source {
      local {
        path = "${local.volume_path}/${local.pv_attrs.namespace}/${local.pv_attrs.name}"
      }
    }

    node_affinity {
      required {
        node_selector_term {
          match_expressions {
            key      = "local/has-volume-${var.backing_volume}"
            operator = "In"
            values   = ["true"]
          }
        }
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim_v1" "this" {
  metadata {
    namespace = var.namespace
    name      = kubernetes_persistent_volume_v1.this.metadata[0].name
  }

  spec {
    access_modes = var.access_modes
    volume_name  = kubernetes_persistent_volume_v1.this.metadata[0].name

    storage_class_name = local.storage_class

    resources {
      requests = {
        storage = kubernetes_persistent_volume_v1.this.spec[0].capacity.storage
      }
    }
  }

  depends_on = [
    kubernetes_persistent_volume_v1.this,
  ]
}
