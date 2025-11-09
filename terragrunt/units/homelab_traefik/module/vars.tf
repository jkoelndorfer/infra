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

variable "traefik_chart" {
  description = "a description of the Traefik chart do download"
  type        = object({ sha256sum = string, url = string })
  default = {
    sha256sum = "692b413f878cb4b3554921ea5bbac113aa128cf89aec4b15cdd39478615a8656"
    url       = "https://traefik.github.io/charts/traefik/traefik-37.1.1.tgz"
  }
}
