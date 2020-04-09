variable "associate_public_ip_address" {
  type        = string
  description = "whether or not to associate a public IP address to instances in this autoscaling group"
}

variable "category" {
  type        = string
  description = "the category of infrastructure that the autoscaling group belongs to"
}

variable "cpu_credits" {
  type        = string
  description = "the CPU credit option for launched instances; can be 'standard' or 'unlimited'"
  default     = "standard"
}

variable "desired_capacity" {
  type        = string
  description = "the initial desired capacity of the autoscaling group (updates to this value are ignored)"
}

variable "dns" {
  type        = string
  default     = ""
  description = "the desired DNS name of instances in this autoscaling group (make sure max_size = 1)"
}

variable "env" {
  type        = string
  description = "the environment that the autoscaling group lives in, e.g. dev or prod"
}

variable "extra" {
  description = "arbitrary extra data to pass to the instance"
  default     = {}
}

variable "iam_instance_profile" {
  type        = string
  default     = ""
  description = "the IAM instance profile that launched instances will assume"
}

variable "instance_type" {
  type        = string
  description = "the type of the EC2 instance, e.g. t3.micro"
}

variable "image_id" {
  type        = string
  description = "the ID of the AMI to launch for instances in this autoscaling group"
}

variable "max_size" {
  type        = string
  description = "the maximum size of the autoscaling group"
}

variable "min_size" {
  type        = string
  description = "the minimum size of the autoscaling group"
}

variable "name" {
  type        = string
  description = "the name of the autoscaling group"
}

variable "role" {
  type        = string
  description = "the role assigned to launched instances (used during provisioning)"
}

variable "security_groups" {
  type        = list
  description = "the list of security groups assigned to instances, in addition to the default"
}

variable "subnet_ids" {
  type        = list
  description = "the list of subnets that instances may come up in"
}
