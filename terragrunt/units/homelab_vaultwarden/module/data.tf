locals {
  log_directory = "/log/"
  smtp = {
    host           = "mail.smtp2go.com"
    port           = 2525
    security       = "starttls"
    from           = "vaultwarden@${var.homelab_shared01_zone.host}"
    auth_mechanism = "Login"
  }
  web_ui_port = 8080
}

module "uid_gid" {
  source = "${var.paths.modules_root}/uid_gid"

  env     = var.env
  service = "vaultwarden"
}
