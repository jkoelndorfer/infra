module "config_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  namespace      = module.namespace.name
  name           = "syncthing-config"
  storage        = "512Mi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume
}

module "data_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  namespace      = module.namespace.name
  name           = "syncthing-data"
  storage        = "200Gi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume
}
