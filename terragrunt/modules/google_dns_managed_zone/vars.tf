variable "description" {
  description = "the description of the DNS zone"
  type        = string
}

variable "dns_name" {
  description = "the DNS name of the prod domain; dev will implicitly be prepended with 'dev.'"
  type        = string
}

variable "enable_dev_zone" {
  description = "if true, a 'dev' zone will be provisioned and appropriate records will be set in prod"
  type        = bool
}

variable "env" {
  description = "the environment that the domain is being deployed into, e.g. 'dev' or 'prod'"
  type        = string
}

variable "function" {
  description = "the value of the 'function' label"
  type        = string
}

variable "project" {
  description = "the project that the zone will be created in"
  type        = object({ project_id = string, labels = map(string) })
}
