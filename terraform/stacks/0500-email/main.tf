module "johnk_io" {
  source = "../../modules/email-zone/v1"

  zone = local.env.johnk_io.zone

  dmarc_record = local.env.dmarc_record
  dkim_records = local.env.johnk_io.dkim_records
  dns_ttl      = local.env.dns_ttl
  mx_records   = local.env.johnk_io.mx_records
  spf_record   = local.env.fastmail_spf_record
}
