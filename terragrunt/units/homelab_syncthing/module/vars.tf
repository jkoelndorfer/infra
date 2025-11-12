variable "backing_volume" {
  description = "the backing volume used for data storage"
  type        = string
  default     = "data0"
}

variable "homelab_shared01_zone" {
  description = "the shared01 sub-zone used for homelab services"
  type        = object({ dns_name = string, host = string, name = string, project = string, zone_was_created = bool })
}

variable "syncthing_gid" {
  description = "the GID that syncthing runs as"
  type        = number
  default     = 911
}

variable "syncthing_uid" {
  description = "the UID that syncthing runs as"
  type        = number
  default     = 911
}
