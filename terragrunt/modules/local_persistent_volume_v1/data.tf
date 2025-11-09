data "kubernetes_nodes" "with_volume" {
  metadata {
    labels = {
      "local/has-volume-${var.backing_volume}" = "true"
    }
  }
}

locals {
  _node = data.kubernetes_nodes.with_volume.nodes[0]
  node = {
    name         = local._node.metadata[0].name
    address      = [for addr in local._node.status[0].addresses : addr["address"] if addr["type"] == "InternalIP"][0]
    hostname     = local._node.metadata[0].labels["kubernetes.io/hostname"]
    pv_directory = "${local._node.metadata[0].annotations["local/path-volume-${var.backing_volume}"]}/${local.pv_attrs.namespace}/${local.pv_attrs.name}"
  }
}
