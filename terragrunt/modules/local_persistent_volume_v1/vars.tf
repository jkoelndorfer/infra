variable "env" {
  description = "the environment that the volume is deployed in"
  type        = string
}

variable "namespace" {
  description = "the namespace that the volume claim is created in"
  type        = string
}

variable "name" {
  description = "the name of the volume and volume claim"
  type        = string
}

variable "storage" {
  description = "the requested storage capacity of the volume"
  type        = string
}

variable "directory_override" {
  description = "optional override values for the storage directory; used to back the PV in a non-standard location"
  nullable    = true
  type = object({
    namespace = string
    name      = string
  })
  default = null
}

variable "access_modes" {
  description = "the volume's access modes"
  type        = list(string)
}

variable "user" {
  description = "the owner of the volume's backing directory"
  type        = number
  default     = 0
}

variable "group" {
  description = "the group of the volume's backing directory"
  type        = number
  default     = 0
}

variable "mode" {
  description = "the mode of the volume's backing directory"
  type        = string
  default     = "0755"
}

variable "skip_directory_management" {
  description = "if true, skips creation, owner, group, and mode management of the directory"
  type        = bool
  default     = false
}

# This is a name we choose.
#
# Currently, with only one node, the only acceptable value is "data0".
# The node must have a label like:
#
#   local/has-volume-${backing_volume}: "true"
#
# To indicate that it is actually configured with the data volume.
variable "backing_volume" {
  description = "the name of the backing disk that the PersistentVolume resides on"
  type        = string
}

# See https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaiming
variable "volume_reclaim_policy" {
  description = "the kubernetes volume reclaim policy"
  type        = string
  default     = "Retain"
}
