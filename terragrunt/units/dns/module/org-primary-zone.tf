module "org_primary_zone" {
  source = "${var.paths.modules_root}/google_dns_managed_zone"

  description     = "organization primary zone"
  dns_name        = var.google_organization.domain
  enable_dev_zone = true
  env             = var.env
  function        = "org-primary"
  project         = module.project
}

module "org_primary_zone_email_records" {
  count  = module.org_primary_zone.zone_was_created ? 1 : 0
  source = "${var.paths.modules_root}/google_email_dns_records"

  addl_apex_txt_rrdata = []
  dkim_rrdata          = "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQClhVsaZVD42oeENdC8L+YseB4Q4mqJrQ/Pr/fokmp/8JCLxR9XsrUIQeK0fDSLzzHA8yNClqmFsYo9kMs4jIDSctyHbZKS+LewVmYZN6evDmshx0nweLuw2fgR27gzH54MCzA36RY/UnS0YW850yMNp2J9A+3ov3qBw9Sfvk0caQIDAQAB"
  dmarc_rrdata         = "v=DMARC1;p=quarantine;pct=100;fo=1;rua=mailto:dmarc@${module.org_primary_zone.email_domain}"
  zone                 = module.org_primary_zone
}
