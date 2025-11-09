module "data_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  env            = var.env
  namespace      = module.namespace.name
  name           = "vaultwarden-data"
  storage        = "50Gi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume

  user  = module.uid_gid.uid
  group = module.uid_gid.gid
  mode  = "0700"
}

module "log_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  env            = var.env
  namespace      = module.namespace.name
  name           = "vaultwarden-log"
  storage        = "10Gi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume

  user  = module.uid_gid.uid
  group = module.uid_gid.gid
  mode  = "0700"
}
