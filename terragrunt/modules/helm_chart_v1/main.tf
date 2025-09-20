module "helm_chart" {
  source = "../http_download"

  url       = var.chart_url
  sha256sum = var.chart_sha256sum
}

resource "kubernetes_manifest" "this" {
  manifest = {
    apiVersion = "helm.cattle.io/v1"
    kind       = "HelmChart"

    metadata = {
      name      = var.name
      namespace = var.namespace
    }

    spec = {
      chartContent = filebase64(module.helm_chart.file_path)

      createNamespace = false
      targetNamespace = var.target_namespace

      timeout = var.timeout

      valuesContent = jsonencode(var.values)
      valuesSecrets = var.values_secrets
    }
  }
}
