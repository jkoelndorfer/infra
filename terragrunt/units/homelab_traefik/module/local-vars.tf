locals {
  ports_by_env = {
    http = {
      dev  = 880
      prod = 80
    }

    https = {
      dev  = 8443
      prod = 443
    }
  }

  http_port  = local.ports_by_env.http[var.env]
  https_port = local.ports_by_env.https[var.env]
}
