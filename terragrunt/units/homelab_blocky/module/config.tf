locals {
  # HCL representation of a Blocky configuration which can
  # be rendered to YAML. See:
  #
  # https://0xerr0r.github.io/blocky/latest/installation/#prepare-your-configuration
  # https://0xerr0r.github.io/blocky/latest/configuration/
  main_config = {
    upstreams = {
      groups = {
        default = [
          # FIXME: Set router IP in a repo-level configuration file accessible
          # by both Terraform and pyinfra. Perhaps use an external data?
          "192.168.192.1",
        ]
      }
    }

    blocking = {
      denylists = {
        ads = [
          "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        ]
      }

      clientGroupsBlock = {
        default = [
          "ads",
        ]
      }
    }

    ports = {
      dns = local.container_dns_port
    }
  }
}

resource "kubernetes_config_map_v1" "blocky" {
  metadata {
    namespace = module.namespace.name
    name      = "blocky"
  }

  data = {
    main = jsonencode(local.main_config)
  }
}
