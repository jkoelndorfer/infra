variable "sha256sum" {
  type        = string
  description = "the sha256sum of the file; this module will fail if the checksum does not match"
}

variable "url" {
  type        = string
  description = "the URL of the file to download"
}
