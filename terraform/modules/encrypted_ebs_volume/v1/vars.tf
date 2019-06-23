variable "availability_zone" {
  type        = "string"
  description = "the availability zone that the EBS volume resides in"
}

variable "category" {
  type        = "string"
  description = "the category of infrastructure that the EBS volume belongs to"
}

variable "role" {
  type        = "string"
  description = "the class of infrastructure that the EBS volume belongs to (used to control attach permissions)"
}

variable "env" {
  type        = "string"
  description = "the environment that the EBS volume lives in, e.g. dev or prod"
}

variable "name" {
  type        = "string"
  description = "the name of the EBS volume"
}

variable "kms_key_arn" {
  type        = "string"
  description = "the ARN of the KMS key used to encrypt the volume"
}

variable "size" {
  type        = "string"
  description = "the size of the EBS volume in gigabytes"
}

variable "type" {
  type        = "string"
  description = "the type of the EBS volume, e.g. gp2"
}
