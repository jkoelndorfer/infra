resource "kubernetes_service_account_v1" "backup" {
  metadata {
    namespace = module.namespace.name
    name      = "backup"
  }
}

resource "kubernetes_cluster_role_v1" "backup" {
  metadata {
    name = "${var.env}-backup"
  }

  rule {
    api_groups = ["apps"]
    resources = [
      "deployments",
    ]
    verbs = [
      "get",
      "list",
      "watch",
    ]
  }

  rule {
    api_groups = ["apps"]
    resources = [
      "deployments/scale",
    ]
    verbs = [
      "patch",
      "update",
    ]
  }
}

resource "kubernetes_cluster_role_binding_v1" "backup" {
  metadata {
    name = "backup"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role_v1.backup.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    namespace = kubernetes_service_account_v1.backup.metadata[0].namespace
    name      = kubernetes_service_account_v1.backup.metadata[0].name
  }
}

resource "kubernetes_role_v1" "backup" {
  metadata {
    namespace = module.namespace.name
    name      = "backup"
  }

  rule {
    api_groups = [""]
    resources = [
      "secrets",
    ]
    verbs = [
      "get",
      "list",
    ]
  }

  rule {
    api_groups = ["argoproj.io"]
    resources = [
      "workflowtaskresults",
    ]
    verbs = [
      "create",
      "get",
      "list",
      "patch",
      "update",
    ]
  }
}

resource "kubernetes_role_binding_v1" "backup" {
  metadata {
    namespace = module.namespace.name
    name      = "backup"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.backup.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    namespace = kubernetes_service_account_v1.backup.metadata[0].namespace
    name      = kubernetes_service_account_v1.backup.metadata[0].name
  }
}
