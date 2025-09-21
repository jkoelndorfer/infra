resource "kubernetes_namespace_v1" "this" {
  metadata {
    name = "${var.env}-${var.name}"
    labels = {
      "local/env"  = var.env
      "local/name" = var.name
    }
  }

  wait_for_default_service_account = true
}
