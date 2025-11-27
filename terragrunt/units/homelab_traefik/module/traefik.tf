module "namespace" {
  source = "${var.paths.modules_root}/kubernetes_namespace_v1"

  env  = var.env
  name = "traefik"
}

module "uid_gid" {
  source = "${var.paths.modules_root}/uid_gid"

  env     = var.env
  service = "traefik"
}

module "cert_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  env            = var.env
  namespace      = module.namespace.name
  name           = "traefik"
  storage        = "128Mi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume

  user  = module.uid_gid.uid
  group = module.uid_gid.gid
}

resource "kubernetes_secret_v1" "traefik_gcp_serviceaccount" {
  metadata {
    namespace = module.namespace.name
    name      = "gcp-service-account"
  }

  data = {
    email = google_service_account.homelab_traefik.email
    key   = base64decode(google_service_account_key.homelab_traefik.private_key)
  }
}

module "traefik_helm_chart" {
  source = "${var.paths.modules_root}/helm_chart_v1"

  name = "traefik"

  chart_url       = var.traefik_chart.url
  chart_sha256sum = var.traefik_chart.sha256sum

  namespace        = module.namespace.name
  target_namespace = module.namespace.name

  set = {}

  values = {
    api = {
      dashboard = true
      insecure  = false
    }

    metrics = {
      prometheus = {
        enabled = false
      }
    }

    certificatesResolvers = {
      gcp = {
        acme = {
          email   = "acme@${var.personal_email_domain}"
          storage = "/data/acme.json"
          dnsChallenge = {
            provider = "gcloud"

            resolvers = [
              "8.8.8.8",
              "8.8.4.4",
            ]
          }
        }
      }
    }

    env = [
      {
        name  = "GCE_PROJECT"
        value = var.homelab_dns_project.project_id
      },
      {
        name  = "GCE_ZONE_ID",
        value = var.homelab_shared01_zone.name
      },
      {
        name = "GCE_SERVICE_ACCOUNT"
        valueFrom = {
          secretKeyRef = {
            name = "gcp-service-account"
            key  = "key"
          }
        }
      },
    ]

    persistence = {
      enabled = true
      name    = "data"
      path    = "/data"

      existingClaim = module.cert_volume.pvc.name
    }

    podSecurityContext = {
      runAsUser  = module.uid_gid.uid
      runAsGroup = module.uid_gid.gid
    }

    gzip = {
      enabled = false
    }

    ports = {
      web = {
        port        = 8888
        exposedPort = local.http_port

        redirections = {
          entryPoint = {
            to        = "websecure"
            scheme    = "https"
            permanent = true
          }
        }
      }

      websecure = {
        port        = 8443
        exposedPort = local.https_port
        asDefault   = true

        tls = {
          enabled      = true
          certResolver = "gcp"
        }
      }
    }

    tlsOptions = {
      default = {
        sniStrict = true
      }
    }
  }

  values_secrets = []
}

resource "kubernetes_manifest" "traefik_dashboard_ingress" {
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "IngressRoute"

    metadata = {
      namespace = module.namespace.name
      name      = "traefik-dashboard"
    }

    spec = {
      routes = [
        {
          match = "Host(`traefik.${var.homelab_shared01_zone.host}`)"
          kind  = "Rule"
          services = [
            {
              name = "api@internal"
              kind = "TraefikService"
            }
          ]
        },
      ]
      tls = {
        domains = [{
          main = "traefik.${var.homelab_shared01_zone.host}"
        }]
      }
    }
  }
}

# See https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/
