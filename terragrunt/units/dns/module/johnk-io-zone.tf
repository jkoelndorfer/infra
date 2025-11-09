module "johnk_io_zone" {
  source = "${var.paths.modules_root}/google_dns_managed_zone"

  description     = "johnk.io"
  dns_name        = "johnk.io"
  enable_dev_zone = false
  env             = var.env
  function        = "johnk-io"
  project         = module.project
}

module "johnk_io_email_records" {
  count  = module.johnk_io_zone.zone_was_created ? 1 : 0
  source = "${var.paths.modules_root}/google_email_dns_records"

  addl_apex_txt_rrdata = [
    "google-site-verification=vZjbCaD_Jb_ACR00pLxQm3_ewS6seMRGwK0-Dq8_4ds",
  ]
  dkim_rrdata  = "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDWYN8FrWcBLOWI7C54HM2NZS093g/K6q6QiH09NmXH1BBW+HFatcpJzN9O95ns0oHHV7Tpii8cYFM09qbX+OoxZGOfgQlaSwyLl36UwgPMGTqgkXrbBlCD1mibgyQ+o0T/v1NCL1c3PyUHS5CM3Xur2HoxImb6el74vvfCWRR6fQIDAQAB"
  dmarc_rrdata = "v=DMARC1;p=none;pct=100;fo=1"
  zone         = module.johnk_io_zone
}
