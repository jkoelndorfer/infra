locals {
  # This is the storage class that ships with k3s to
  # configure local directories.
  #
  # See https://docs.k3s.io/storage
  storage_class = "local-path"

  pv_attrs = var.directory_override != null ? var.directory_override : { namespace = var.namespace, name = var.name }

  directory_current = {
    user  = try(tonumber(data.external.directory.result.user), -1)
    group = try(tonumber(data.external.directory.result.group), -1)
    mode  = try(data.external.directory.result.mode, "unset")
  }

  directory_desired = {
    user  = var.user
    group = var.group
    mode  = var.mode
  }
}

data "external" "directory" {
  program = ["${path.module}/pvdata"]

  query = {
    REMOTE_HOST  = local.node.address
    PV_DIRECTORY = local.node.pv_directory
  }
}

resource "null_resource" "directory" {
  count = var.skip_directory_management ? 0 : 1

  triggers = {
    reprovision = local.directory_current == local.directory_desired ? "ok" : uuid()
  }

  provisioner "local-exec" {
    command = "${path.module}/pvsetup"

    environment = {
      PV_DIRECTORY = local.node.pv_directory
      PV_USER      = var.user
      PV_GROUP     = var.group
      PV_MODE      = var.mode
      REMOTE_HOST  = local.node.address
    }
  }

  lifecycle {
    precondition {
      condition     = length(data.kubernetes_nodes.with_volume.nodes) == 1
      error_message = "expected to find exactly one node with backing volume ${var.backing_volume}; found ${length(data.kubernetes_nodes.with_volume)}"
    }
  }
}

resource "kubernetes_persistent_volume_v1" "this" {
  metadata {
    name = "${var.env}-${var.name}"
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
        path = local.node.pv_directory
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

  depends_on = [null_resource.directory]
}

resource "kubernetes_persistent_volume_claim_v1" "this" {
  metadata {
    namespace = var.namespace
    name      = var.name
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
