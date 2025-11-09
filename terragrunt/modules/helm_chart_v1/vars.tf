variable "name" {
  type        = string
  description = "the name of the HelmChart Kubernetes resource"
}

variable "namespace" {
  type        = string
  description = "the namespace that the HelmChart resource is created in"
}

variable "chart_url" {
  type        = string
  description = "URL of chart to deploy (.tgz archive)"
}

variable "chart_sha256sum" {
  type        = string
  description = "sha256sum of the chart given in chart_url"
}

variable "set" {
  description = "overrides for chart values; these take highest precedence"
  default     = {}
}

variable "target_namespace" {
  type        = string
  description = "the namespace that the Helm chart deploys resources into"
}

variable "timeout" {
  type        = string
  description = "timeout for Helm operations as a duration string (300s, 10m, 1h, etc)"
  default     = "5m0s"
}

variable "values" {
  description = "values that are passed to the Helm chart"
  default     = {}
}

# See https://docs.k3s.io/helm#chart-values-from-secrets.
variable "values_secrets" {
  type        = list(object({ name = string, ignoreUpdates = optional(bool), keys = list(string) }))
  description = "values that are passed to the Helm chart via secrets"
  default     = null
}
