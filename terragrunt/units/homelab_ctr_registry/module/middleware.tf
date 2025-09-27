resource "random_string" "registry_ro_password" {
  length  = 32
  lower   = true
  upper   = true
  numeric = true
  special = false
}

resource "kubernetes_secret_v1" "registry_ro" {
  metadata {
    namespace = module.namespace.name
    name      = "registry-ro"
  }

  type = "kubernetes.io/basic-auth"

  data = {
    username = "registry-ro"
    password = random_string.registry_ro_password.result
    hostname = local.registry_ro_host
  }
}

resource "kubernetes_manifest" "registry_middleware_ro" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "Middleware"

    metadata = {
      namespace = module.namespace.name
      name      = "registry-ro"
    }

    spec = {
      basicAuth = {
        secret = kubernetes_secret_v1.registry_ro.metadata[0].name
      }
    }
  }

  depends_on = [
    kubernetes_secret_v1.registry_ro,
  ]
}

resource "random_string" "registry_rw_password" {
  length  = 32
  lower   = true
  upper   = true
  numeric = true
  special = false
}

resource "kubernetes_secret_v1" "registry_rw" {
  metadata {
    namespace = module.namespace.name
    name      = "registry-rw"
  }

  type = "kubernetes.io/basic-auth"

  data = {
    username = "registry-rw"
    password = random_string.registry_rw_password.result
    hostname = local.registry_rw_host
  }
}

resource "kubernetes_manifest" "registry_middleware_rw" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "Middleware"

    metadata = {
      namespace = module.namespace.name
      name      = "registry-rw"
    }

    spec = {
      basicAuth = {
        secret = kubernetes_secret_v1.registry_rw.metadata[0].name
      }
    }
  }
}

# The registry dummy password is used to make Traefik always return
# 401 Unauthorized for the registry-ro hostname when using HTTP
# methods that perform writes.
resource "random_string" "registry_dummy_password" {
  length  = 32
  lower   = true
  upper   = true
  numeric = true
  special = false
}

resource "kubernetes_secret_v1" "registry_dummy" {
  metadata {
    namespace = module.namespace.name
    name      = "registry-dummy"
  }

  type = "kubernetes.io/basic-auth"

  data = {
    username = "registry-dummy"
    password = random_string.registry_dummy_password.result
  }
}

resource "kubernetes_manifest" "registry_middleware_dummy" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "Middleware"

    metadata = {
      namespace = module.namespace.name
      name      = "registry-dummy"
    }

    spec = {
      basicAuth = {
        secret = kubernetes_secret_v1.registry_dummy.metadata[0].name
      }
    }
  }
}
