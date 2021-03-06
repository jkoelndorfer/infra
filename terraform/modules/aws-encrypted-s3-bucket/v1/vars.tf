variable "bucket" {
  type        = string
  description = "the name of the S3 bucket"
}

variable "category" {
  type        = string
  description = "the category of infrastructure that the S3 bucket belongs to"
}

variable "env" {
  type        = string
  description = "the environment that the bucket lives in, e.g. dev or prod"
}

variable "region" {
  type        = string
  description = "the AWS region that the S3 bucket is hosted in"
}

variable "versioning" {
  type        = string
  description = "whether or not to enable versioning on the bucket"
}
