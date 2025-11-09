variable "argo_workflows_chart" {
  description = "a description of the Argo Workflows chart do download"
  type        = object({ sha256sum = string, url = string })
  default = {
    sha256sum = "04b8550a40a980aefad1f4cf34bd33779c45ac5bb7ea97be81f8180050766368"
    url       = "https://github.com/argoproj/argo-helm/releases/download/argo-workflows-0.45.26/argo-workflows-0.45.26.tgz"
  }
}

variable "homelab_shared01_zone" {
  description = "the shared01 sub-zone used for homelab services"
  type        = object({ dns_name = string, host = string, name = string, project = string, zone_was_created = bool })
}

variable "server_service_port_name" {
  description = "name of the service port for the Argo Workflows server"
  type        = string
  default     = "argo-workflows-server"
}
