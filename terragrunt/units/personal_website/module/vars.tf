variable "dns_project" {
  description = "GCP project hosting DNS zones"
  type        = object({ project_id = string })
}

variable "personal_zone" {
  description = "the zone servicing DNS for my personal website"
  type        = object({ dns_name = string, host = string, name = string })
}
