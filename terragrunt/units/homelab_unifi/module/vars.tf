variable "backing_volume" {
  description = "the backing volume used for data storage"
  type        = string
  default     = "data0"
}

variable "homelab_shared01_zone" {
  description = "the shared01 sub-zone used for homelab services"
  type        = object({ dns_name = string, host = string, name = string, project = string, zone_was_created = bool })
}

variable "unifi_image" {
  description = "UniFi Controller image to run"
  type        = string
  default     = "linuxserver/unifi-controller:7.3.76-ls174"
}
