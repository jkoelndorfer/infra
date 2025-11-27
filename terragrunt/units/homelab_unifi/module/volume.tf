module "config_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  env            = var.env
  namespace      = module.namespace.name
  name           = "unifi-config"
  storage        = "10Gi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume
}
