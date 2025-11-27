module "uid_gid" {
  source = "${var.paths.modules_root}/uid_gid"

  env     = var.env
  service = "unifi"
}
