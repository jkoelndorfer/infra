module "namespace" {
  source = "${var.paths.modules_root}/kubernetes_namespace_v1"

  env  = var.env
  name = "unifi"
}
