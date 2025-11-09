variable "backing_volume" {
  description = "the backing volume used for data storage"
  type        = string
  default     = "data0"
}

variable "homelab_shared01_zone" {
  description = "the shared01 sub-zone used for homelab services"
  type        = object({ dns_name = string, host = string, name = string, project = string, zone_was_created = bool })
}

variable "vaultwarden_image" {
  description = "the docker image to use to run Vaultwarden"
  type        = string
  default     = "vaultwarden/server:1.32.0"
}
