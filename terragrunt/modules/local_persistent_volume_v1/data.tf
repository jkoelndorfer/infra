data "kubernetes_nodes" "with_volume" {
  metadata {
    labels = {
      "local/has-volume-${var.backing_volume}" = "true"
    }
  }
}

locals {
  node_with_volume = data.kubernetes_nodes.with_volume.nodes[0]
  volume_path      = local.node_with_volume.metadata[0].annotations["local/path-volume-${var.backing_volume}"]
}
