variable "backing_volume" {
  description = "the backing volume used for data storage"
  type        = string
  default     = "data0"
}

variable "homelab_shared01_zone" {
  description = "the shared01 sub-zone used for homelab services"
  type        = object({ dns_name = string, host = string, name = string, project = string, zone_was_created = bool })
}

variable "homelab_dns_project" {
  description = "the GCP project that homelab DNS zone(s) are configured in"
  type        = object({ project_id = string })
}

variable "homelab_dns_updater_role" {
  description = "the custom role that grants access to update homelab DNS zone(s)"
  type        = object({ id = string, permissions = list(string), role_id = string })
}

# See available Traefik chart releases at:
#
# https://github.com/traefik/traefik-helm-chart/releases
variable "traefik_chart" {
  description = "a description of the Traefik chart to download"
  type        = object({ sha256sum = string, url = string })
  default = {
    sha256sum = "04819a82ef6aa90ee28e5a01269e5b4414149d585c3bc938b66afa64dc78a595"
    url       = "https://traefik.github.io/charts/traefik/traefik-37.4.0.tgz"
  }
}
