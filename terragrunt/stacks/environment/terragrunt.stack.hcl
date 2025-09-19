locals {
  units_dir  = "${get_repo_root()}/terragrunt//units"
  unit_paths = {
    google_env_folder = "google_env_folder"
    backup            = "backup"
    dns               = "dns"
    homelab_dns       = "homelab_dns"
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
