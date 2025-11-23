variable "backing_volume" {
  description = "the name of the backing PersistVolume that local backups reside on"
  type        = string
  default     = "data0"
}

variable "backup_image" {
  description = "the backup container image to use; must be present in the local registry"
  type        = string
  default     = "backupjob:latest"
}

variable "backup_time" {
  description = "the time that the backup runs"
  type        = object({ timezone = string, hour = number, minute = number })
  default = {
    timezone = "America/Chicago"
    hour     = 3
    minute   = 0
  }
}

variable "registry_ro_secret" {
  description = "secret containing information for read-only container registry access"
  type        = object({ namespace = string, name = string })
}

variable "syncthing_config_volume" {
  description = "the persistent volume containing syncthing config"
  type = object({
    access_modes   = list(string)
    backing_volume = string
    env            = string
    pv             = object({ name = string })
    pvc            = object({ namespace = string, name = string })
    storage        = string
  })
}

variable "syncthing_data_volume" {
  description = "the persistent volume containing syncthing data"
  type = object({
    access_modes   = list(string)
    backing_volume = string
    env            = string
    group          = number
    pv             = object({ name = string })
    pvc            = object({ namespace = string, name = string })
    storage        = string
    user           = number
  })
}

variable "syncthing_deployment" {
  description = "the deployment supporting the syncthing service"
  type        = object({ namespace = string, name = string })
}

variable "vaultwarden_data_volume" {
  description = "the persistent volume containing vaultwarden data"
  type = object({
    access_modes   = list(string)
    backing_volume = string
    env            = string
    group          = number
    pv             = object({ name = string })
    pvc            = object({ namespace = string, name = string })
    storage        = string
    user           = number
  })
}

variable "vaultwarden_deployment" {
  description = "the deployment supporting the vaultwarden service"
  type        = object({ namespace = string, name = string })
}
