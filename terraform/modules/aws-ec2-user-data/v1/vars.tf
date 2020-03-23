variable "asg_name" {
  type        = string
  description = "the name of the autoscaling group that the instance belongs to"
}

variable "category" {
  type        = string
  description = "category of infrastructure that the instance belongs to"
}

variable "dns" {
  type        = string
  default     = null
  description = "DNS record pointing to instance; used to set the hostname"
}

variable "env" {
  type        = string
  description = "environment that the instance belongs to, e.g. dev or prod"
}

variable "extra" {
  description = "arbitrary extra data to pass to the instance"
  default     = {}
}

variable "name" {
  type        = string
  description = "name assigned to instance"
}
