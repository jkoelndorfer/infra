variable "domain" {
  description = "the domain of the site"
  type        = string
}

variable "project" {
  description = "the GCP project that DNS is hosted in"
  type        = string
}

variable "zone_name" {
  description = "the name of the GCP zone DNS is hosted in"
  type        = string
}
