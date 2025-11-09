locals {
  # See https://docs.syncthing.net/users/firewall.html
  ports_by_env = {
    dev = {
      web_ui        = 8385
      sync_protocol = 22001
    }

    prod = {
      web_ui        = 8384
      sync_protocol = 22000
    }
  }

  web_ui_port        = local.ports_by_env[var.env].web_ui
  sync_protocol_port = local.ports_by_env[var.env].sync_protocol
}
