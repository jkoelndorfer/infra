variable "env" {
  type        = "string"
  description = "the environment that the EC2 role belongs to, e.g. dev or prod"
}

variable "name" {
  type        = "string"
  description = "the name of the EC2 role"
}
