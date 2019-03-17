variable "category" {
  type        = "string"
  description = "the category of infrastructure that the VPC belongs to"
}

variable "cidr_block" {
  type        = "string"
  description = "the CIDR block assigned to the VPC, e.g. 10.0.0.0/16"
}

variable "env" {
  type        = "string"
  description = "the environment that the VPC belongs to, e.g. dev or prod"
}

variable "name" {
  type        = "string"
  description = "the name of the VPC"
}

variable "ssh_port" {
  type        = "string"
  description = "the port used for management of systems via SSH, e.g. 22"
}
