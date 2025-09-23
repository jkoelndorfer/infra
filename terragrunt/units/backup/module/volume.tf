# This points at syncthing's data volume using the directory_override parameter.
module "syncthing_data_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  directory_override = {
    namespace = var.syncthing_data_volume.pvc.namespace,
    name      = var.syncthing_data_volume.pvc.name,
  }
  env            = var.env
  namespace      = module.namespace.name
  name           = "syncthing-data-backup"
  storage        = "200Gi"
  access_modes   = ["ReadOnlyMany"]
  backing_volume = var.syncthing_data_volume.backing_volume
}

module "local_backup_volume" {
  source = "${var.paths.modules_root}/local_persistent_volume_v1"

  env            = var.env
  namespace      = module.namespace.name
  name           = "local-backup"
  storage        = "300Gi"
  access_modes   = ["ReadWriteOnce"]
  backing_volume = var.backing_volume
}
