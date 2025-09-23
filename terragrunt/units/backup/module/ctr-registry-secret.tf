data "kubernetes_secret_v1" "registry_ro" {
  metadata {
    namespace = var.registry_ro_secret.namespace
    name      = var.registry_ro_secret.name
  }
}

resource "kubernetes_secret_v1" "registry_image_pull" {
  metadata {
    namespace = module.namespace.name
    name      = "image-pull"
  }

  type = "kubernetes.io/dockerconfigjson"

  data = {
    ".dockerconfigjson" = jsonencode({
      auths = {
        "${data.kubernetes_secret_v1.registry_ro.data.hostname}/" = {
          username = data.kubernetes_secret_v1.registry_ro.data.username
          password = data.kubernetes_secret_v1.registry_ro.data.password
        }
      }
    })
  }
}
