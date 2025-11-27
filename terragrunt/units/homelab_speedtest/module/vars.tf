variable "homelab_shared01_zone" {
  description = "the shared01 sub-zone used for homelab services"
  type        = object({ dns_name = string, host = string, name = string, project = string, zone_was_created = bool })
}

variable "image" {
  description = "speed test image to run"
  type        = string
  default     = "openspeedtest/latest:v2.0.6"
}
