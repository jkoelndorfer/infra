locals {
  registry_port    = 5000
  registry_ro_host = "ctr-registry-ro.${var.homelab_shared01_zone.host}"
  registry_rw_host = "ctr-registry-rw.${var.homelab_shared01_zone.host}"
}
