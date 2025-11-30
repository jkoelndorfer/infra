locals {
  container_dns_port = 5353
  dns_port           = 53
}

module "uid_gid" {
  source = "${var.paths.modules_root}/uid_gid"

  env     = var.env
  service = "blocky"
}
