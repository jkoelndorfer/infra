locals {
  # These are the base UIDs and GIDs for dev and prod.
  #
  # UIDs and GIDs below are defined as offsets starting
  # at these ranges.
  base_ids = {
    dev  = 100000
    prod = 200000
  }

  # These are the IDs for each service. As noted above, the IDs
  # specified here are *offsets from the base ID*. The base ID
  # is dependent upon the environment.
  service_ids = {
    traefik      = 0
    ctr_registry = 1
    syncthing    = 2
    backup       = 3
    vaultwarden  = 4
  }

  service_id = local.base_ids[var.env] + local.service_ids[var.service]
}
