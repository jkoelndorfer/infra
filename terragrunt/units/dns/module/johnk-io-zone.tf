module "johnk_io_zone" {
  source = "${var.paths.modules_root}/google_dns_managed_zone"

  description     = "johnk.io"
  dns_name        = "johnk.io"
  enable_dev_zone = false
  env             = var.env
  function        = "johnk-io"
  project         = module.project
}
