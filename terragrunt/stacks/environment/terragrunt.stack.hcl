locals {
  units_dir  = "${get_repo_root()}/terragrunt//units"
  unit_paths = {
    google_env_folder      = "google_env_folder"
    backup                 = "backup"
    dns                    = "dns"
    homelab_argo_workflows = "homelab_argo_workflows"
    homelab_ctr_registry   = "homelab_ctr_registry"
    homelab_dns            = "homelab_dns"
    homelab_traefik        = "homelab_traefik"
    homelab_syncthing      = "homelab_syncthing"
    homelab_vaultwarden    = "homelab_vaultwarden"
  }
  unit_paths_values = { for k, v in local.unit_paths: k => "../${v}" }

  common_values = {
    env        = values.env
    unit_paths = local.unit_paths_values

    mock_outputs = {
      google_env_folder = {
        google_env_folder = {
          env          = values.env
          display_name = "not a real environment folder; use only env attribute"
          name         = "not a real environment folder; use only env attribute"
          folder_id    = "000000000000"
        }
      }
      homelab_ctr_registry = {
        registry_ro_host = "ctr-registry-ro.example.com"
        registry_rw_host = "ctr-registry-rw.example.com"
      }
      homelab_dns = {
        homelab_dns_project = {
          folder = "mock-folder"
          labels = {
            env = "mock"
          }
          id     = "mock-project-foo"
          name   = "mock-project"
          number = "000000000000"
        }
        homelab_shared01_zone = {
          zone_was_created = true
          name             = "homelab-example-com"
          dns_name         = "homelab.example.com."
          email_domain     = "homelab.example.com"
          host            =  "homelab.example.com"
          name_servers     = ["ns1.examplens.com", "ns2.examplens.com"]
          project          = "mock-homelab-dns"

        }
        homelab_dns_updater_role = {
          id          = "projects/mock/role/custom.dns.recordUpdater"
          permissions = [
            "dns.changes.create",
          ]
          description = "Mock role to provide access to update DNS records."
        }
      }
      homelab_syncthing = {
        deployment = {
          namespace = "mock-syncthing"
          name      = "syncthing"
        }

        data_volume = {
          name    = "mock-syncthing-data"
          storage = "100Gi"

          storage_class_name = "local-path"
        }
      }
      homelab_traefik = {}
      homelab_vaultwarden = {
        deployment = {
          namespace = "mock-vaultwarden"
          name      = "vaultwarden"
        }

        data_volume = {
          name    = "mock-vaultwarden-data"
          storage = "50Gi"

          storage_class_name = "local-path"
        }
      }
    }
  }
}

unit "google_env_folder" {
  source = "${local.units_dir}/google_env_folder"
  path   = local.unit_paths.google_env_folder
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "homelab_dns" {
  source = "${local.units_dir}/homelab_dns"
  path   = local.unit_paths.homelab_dns
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "dns" {
  source = "${local.units_dir}/dns"
  path   = local.unit_paths.dns
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "backup" {
  source = "${local.units_dir}/backup"
  path   = local.unit_paths.backup
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "homelab_traefik" {
  # Traefik's Helm chart does not support multiple installations per Kubernetes cluster.
  #
  # It produces the following error:
  #   > Error: INSTALLATION FAILED: Unable to continue with install: IngressClass "traefik" in namespace ""
  #   > exists and cannot be imported into the current release: invalid ownership metadata; annotation validation
  #   > error: key "meta.helm.sh/release-namespace" must equal "foo": current value is "bar"
  source = values.env == "prod" ? "${local.units_dir}/homelab_traefik" : "${local.units_dir}/noop"
  path   = local.unit_paths.homelab_traefik
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "homelab_ctr_registry" {
  source = "${local.units_dir}/homelab_ctr_registry"
  path   = local.unit_paths.homelab_ctr_registry
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "homelab_argo_workflows" {
  # Argo Workflows monitors resources in all namespaces, so it won't
  # support multiple installations per Kubernetes cluster.
  source = values.env == "prod" ? "${local.units_dir}/homelab_argo_workflows" : "${local.units_dir}/noop"
  path   = local.unit_paths.homelab_argo_workflows
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "homelab_syncthing" {
  source = "${local.units_dir}/homelab_syncthing"
  path   = local.unit_paths.homelab_syncthing
  values = local.common_values

  no_dot_terragrunt_stack = true
}

unit "homelab_vaultwarden" {
  source = "${local.units_dir}/homelab_vaultwarden"
  path   = local.unit_paths.homelab_vaultwarden
  values = local.common_values

  no_dot_terragrunt_stack = true
}
