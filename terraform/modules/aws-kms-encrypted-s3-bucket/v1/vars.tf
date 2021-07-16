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

variable "kms_key_id" {
  type        = string
  description = "the ID of the KMS key used to encrypt the bucket"
}

variable "versioning" {
  type        = string
  description = "whether or not to enable versioning on the bucket"
}
