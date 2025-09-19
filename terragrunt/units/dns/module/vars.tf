variable "homelab_shared01_zone" {
  description = "the zone created to provide homelab public DNS"
  type        = object({ dns_name = string, name = string, name_servers = list(string), project = string })
}
