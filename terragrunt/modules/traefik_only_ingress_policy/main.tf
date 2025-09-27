resource "kubernetes_network_policy_v1" "this" {
  metadata {
    namespace = var.namespace
    name      = "traefik-only"
  }

  spec {
    # The ingress policy applies to all pods in the namespace.
    pod_selector {}

    policy_types = ["Ingress"]

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "local/name" = "traefik"
          }
        }
      }
    }
  }
}
