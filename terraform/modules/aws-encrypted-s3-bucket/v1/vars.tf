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

variable "lifecycle_rules" {
  type = list(object({
    id                             = string,
    prefix                         = string,
    transitions                    = list(object({ days = number, storage_class = string })),
    noncurrent_version_expiration  = object({ days = number }),
    noncurrent_version_transitions = list(object({ days = number, storage_class = string })),
  }))
}

variable "versioning" {
  type        = string
  description = "whether or not to enable versioning on the bucket"
}
