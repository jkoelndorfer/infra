module "namespace" {
  source = "${var.paths.modules_root}/kubernetes_namespace_v1"

  env  = var.env
  name = "argo-workflows"
}

module "argo_workflows_helm_chart" {
  source = "${var.paths.modules_root}/helm_chart_v1"

  name = "argo-workflows"

  chart_url       = var.argo_workflows_chart.url
  chart_sha256sum = var.argo_workflows_chart.sha256sum

  namespace        = module.namespace.name
  target_namespace = module.namespace.name

  set = {}

  # See:
  #   * https://github.com/argoproj/argo-helm/blob/7bf2ed4315b88cdd9438695b443de504f4ee9a66/charts/argo-workflows/README.md
  #   * https://github.com/argoproj/argo-helm/blob/7bf2ed4315b88cdd9438695b443de504f4ee9a66/charts/argo-workflows/values.yaml
  values = {
    namespaceOverride = module.namespace.name

    controller = {
      workflowWorkers     = 2
      workflowTTLWorkers  = 2
      podCleanupWorkers   = 1
      cronWorkflowWorkers = 2
    }

    server = {
      authModes = [
        "server",
      ]
      servicePortName = var.server_service_port_name
    }
  }
}
