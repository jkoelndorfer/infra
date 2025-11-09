module "data_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  env            = var.env
  namespace      = module.namespace.name
  name           = "data"
  storage        = "50Gi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume
}
